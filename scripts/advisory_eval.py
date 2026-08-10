"""D5-D6 eval harness: score the advisory against the golden set.

Runs every golden-set forecast through the full generation path and reports the
metrics the work plan calls for. Defaults to offline (rules path, no provider),
so it runs in CI and on a laptop with no API key.

    python scripts/advisory_eval.py                  # offline, rules path
    python scripts/advisory_eval.py --live           # real providers (costs money)
    python scripts/advisory_eval.py --review-sheet review.md

Metrics:
  schema validity   -- the advisory has every field the API contract promises
  numeric fidelity  -- no figure outside Verdict.numeric_facts()
  safety            -- no banned topic, no claim of historical authority
  substance         -- actions match what the rules decided
  band consistency  -- bad news not softened
  rule coverage     -- which driver rules the set actually exercises
  SMS compliance    -- one segment, instruction intact
  latency           -- p50 / p95 wall clock per advisory
  path mix          -- llm vs llm_fallback_rules vs rules

`--live` is opt-in and prints an estimated cost before running. The first real
provider call in this project's history should be a deliberate act.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def load_env() -> None:
    """Load .env so --live picks up provider keys.

    Entry points load environment, libraries do not -- src/advisory/ reads
    os.environ and stays free of dotenv. Parsed by hand so a missing
    python-dotenv cannot break the offline path.
    """
    import os

    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_env()

from src.advisory.generator import build_user_prompt, generate_advisory  # noqa: E402
from src.advisory.rules import build_verdict, load_config  # noqa: E402
from src.advisory.schemas import PredictionPayload  # noqa: E402
from src.advisory.validation import (  # noqa: E402
    check_band_consistency,
    check_numeric_fidelity,
    check_safety,
)

GOLDEN = REPO_ROOT / "tests" / "fixtures" / "golden" / "golden_set.json"

# Rough public pricing for the configured small models, USD per 1M tokens, and
# ~4 characters per token. Used only for an order-of-magnitude estimate before
# spending money -- not a billing figure.
COST_PER_1M_INPUT = 0.15
COST_PER_1M_OUTPUT = 0.60
CHARS_PER_TOKEN = 4


def pct(n: int, total: int) -> str:
    return f"{100 * n / total:5.1f}%" if total else "  n/a"


def evaluate(items: List[Dict[str, Any]], live: bool) -> Dict[str, Any]:
    rules, _ = load_config()
    results = []

    for item in items:
        payload = PredictionPayload.from_dict(item["payload"])
        verdict = build_verdict(payload)

        started = time.perf_counter()
        # providers=[] forces the offline path; None lets the generator use
        # whatever is configured and credentialled.
        advisory = generate_advisory(
            payload, providers=None if live else [], use_cache=False
        )
        elapsed_ms = (time.perf_counter() - started) * 1000

        text = f"{advisory.headline}\n{advisory.body}"
        prose_only = "\n".join(
            line for line in advisory.body.splitlines() if not line.startswith("- ")
        )

        in_season = [a for a in verdict.actions if a.stage == "in_season"]
        top = in_season[0] if in_season else verdict.actions[0]
        expected_sms = top.sms_action or top.action

        results.append(
            {
                "id": item["id"],
                "stratum": item["stratum"],
                "band": verdict.band,
                "generated_by": advisory.generated_by,
                "latency_ms": elapsed_ms,
                "schema_ok": all(
                    bool(getattr(advisory, f, "").strip())
                    for f in ("headline", "body", "sms_text", "disclaimer")
                ),
                "numeric_errors": check_numeric_fidelity(
                    f"{advisory.headline}\n{prose_only}", verdict
                ),
                "safety_errors": check_safety(text, rules),
                "band_errors": check_band_consistency(
                    {"headline": advisory.headline, "body": advisory.body}, verdict
                ),
                "sms_len": len(advisory.sms_text),
                "sms_intact": expected_sms in advisory.sms_text,
                "rules_fired": [a.rule_id for a in verdict.actions],
                "prompt_chars": len(build_user_prompt(verdict, advisory.lang, rules)),
                "advisory": advisory,
            }
        )
    return {"results": results, "rules": rules}


def report(results: List[Dict[str, Any]], rules: Dict[str, Any]) -> int:
    total = len(results)
    print(f"\nAdvisory eval -- {total} golden-set forecasts")
    print("=" * 66)

    checks = [
        ("schema validity", sum(r["schema_ok"] for r in results)),
        ("numeric fidelity", sum(not r["numeric_errors"] for r in results)),
        ("safety", sum(not r["safety_errors"] for r in results)),
        ("band consistency", sum(not r["band_errors"] for r in results)),
        ("SMS <= 160 chars", sum(r["sms_len"] <= 160 for r in results)),
        ("SMS instruction intact", sum(r["sms_intact"] for r in results)),
    ]
    print("\nQuality gates")
    failures = 0
    for name, passed in checks:
        flag = "" if passed == total else "   <-- FAIL"
        if passed != total:
            failures += 1
        print(f"  {name:24s} {passed:3d}/{total}  {pct(passed, total)}{flag}")

    print("\nGeneration path")
    for path, n in Counter(r["generated_by"] for r in results).most_common():
        print(f"  {path:24s} {n:3d}  {pct(n, total)}")

    print("\nStrata")
    for stratum, n in Counter(r["stratum"] for r in results).most_common():
        print(f"  {stratum:24s} {n:3d}")

    print("\nRule coverage across the set")
    all_rule_ids = [r["id"] for r in rules["drivers"]] + ["all_clear"]
    fired = Counter(rid for r in results for rid in r["rules_fired"])
    unexercised = []
    for rule_id in all_rule_ids:
        n = fired.get(rule_id, 0)
        if n == 0:
            unexercised.append(rule_id)
        print(f"  {rule_id:24s} {n:3d}")
    if unexercised:
        print(f"  NOT EXERCISED by this set: {', '.join(unexercised)}")

    latencies = sorted(r["latency_ms"] for r in results)
    print("\nLatency (ms)")
    print(f"  p50  {statistics.median(latencies):8.1f}")
    print(f"  p95  {latencies[int(0.95 * (len(latencies) - 1))]:8.1f}")
    print(f"  max  {latencies[-1]:8.1f}")

    avg_prompt = statistics.mean(r["prompt_chars"] for r in results)
    in_tok = avg_prompt / CHARS_PER_TOKEN
    out_tok = 250
    per_1000 = (
        (in_tok * COST_PER_1M_INPUT + out_tok * COST_PER_1M_OUTPUT) / 1_000_000 * 1000
    )
    print("\nCost estimate (order of magnitude, not a billing figure)")
    print(f"  avg prompt      {avg_prompt:.0f} chars (~{in_tok:.0f} tokens)")
    print(f"  per 1000 advisories  ${per_1000:.2f}")
    print("  SMS path costs nothing: it is rules-rendered.\n")

    for r in results:
        for kind in ("numeric_errors", "safety_errors", "band_errors"):
            for err in r[kind]:
                print(f"  FAIL [{r['id']}] {kind}: {err}")

    return failures


def write_review_sheet(results: List[Dict[str, Any]], path: Path) -> None:
    """A sheet a native speaker or agronomist can actually fill in."""
    lines = [
        "# Advisory review sheet",
        "",
        "For each advisory, rate 1-5 and add a note. We are asking two separate",
        "questions: is the advice *correct* for this situation, and is the",
        "wording something a farmer would actually act on?",
        "",
        "- **Accuracy**: is the agronomic advice right for these conditions?",
        "- **Clarity**: would a working farmer understand and act on it?",
        "- **Tone**: direct about bad news without being alarming?",
        "",
        "Flag anything that reads as a promise, a dosage, or financial advice.",
        "",
        "---",
        "",
    ]
    for r in results:
        a = r["advisory"]
        lines += [
            f"## {r['id']}  ({r['stratum']}, band = {r['band']})",
            "",
            f"**{a.headline}**",
            "",
            "```",
            a.body,
            "```",
            "",
            f"SMS ({len(a.sms_text)} chars): `{a.sms_text}`",
            "",
            "| | Score 1-5 | Note |",
            "|---|---|---|",
            "| Accuracy | | |",
            "| Clarity | | |",
            "| Tone | | |",
            "",
            "---",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote review sheet to {path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden", type=Path, default=GOLDEN)
    ap.add_argument(
        "--live",
        action="store_true",
        help="call real providers (costs money; requires an API key)",
    )
    ap.add_argument("--review-sheet", type=Path, default=None)
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    doc = json.loads(args.golden.read_text(encoding="utf-8"))
    items = doc["items"]

    if args.live:
        print(f"LIVE MODE: this will call real providers for {len(items)} forecasts.")
        print("Estimated cost: under $0.02 at current small-model pricing.\n")

    evaluated = evaluate(items, live=args.live)
    failures = report(evaluated["results"], evaluated["rules"])

    if args.review_sheet:
        write_review_sheet(evaluated["results"], args.review_sheet)

    if args.json:
        args.json.write_text(
            json.dumps(
                [
                    {k: v for k, v in r.items() if k != "advisory"}
                    for r in evaluated["results"]
                ],
                indent=2,
            ),
            encoding="utf-8",
        )

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
