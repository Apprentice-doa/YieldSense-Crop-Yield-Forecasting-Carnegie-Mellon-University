"""Demo driver: warm the cache, then show the advisory in every language.

Built for demo day. A live demo that calls an LLM in front of an audience will
eventually fail on conference wifi, a rate limit, or a content filter, and the
fallback -- correct as it is -- is not what you want to be showing.

So: `--warm` generates every advisory ahead of time into a cache file, and the
demo itself replays from that file with no network at all. `--check` verifies
the cache covers what you are about to present.

    python scripts/advisory_demo.py --warm     # once, on good wifi
    python scripts/advisory_demo.py --check    # before you walk on stage
    python scripts/advisory_demo.py            # the demo itself, offline

Without a warmed cache the demo still runs -- it just shows the deterministic
rules text, which is the honest fallback and worth showing anyway.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def load_env() -> None:
    import os

    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_env()

from src.advisory.generator import generate_advisory  # noqa: E402
from src.advisory.metrics import collector  # noqa: E402
from src.advisory.schemas import PredictionPayload  # noqa: E402

GOLDEN = REPO_ROOT / "tests" / "fixtures" / "golden" / "golden_set.json"
CACHE_FILE = REPO_ROOT / "tests" / "fixtures" / "golden" / "demo_cache.json"

# One case per story we want to tell, not a random sample.
DEMO_CASES = [
    ("critical_1", "A season going badly — the advisory farmers most need"),
    ("above_1", "A good season — post-harvest planning is the value here"),
    ("low_confidence", "The model is unsure, and says so"),
    ("dq_invalid_ndvi", "Bad satellite data — advice is withheld, not guessed"),
    ("unknown_crop", "A crop we have no baseline for — degrades honestly"),
]
DEMO_LANGS = ["en", "sw", "rw", "fr"]


def load_cases() -> List[Dict[str, Any]]:
    doc = json.loads(GOLDEN.read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in doc["items"]}
    cases = []
    for case_id, story in DEMO_CASES:
        if case_id not in by_id:
            print(f"  !! golden set has no '{case_id}' — skipping")
            continue
        cases.append({**by_id[case_id], "story": story})
    return cases


def cache_key(case_id: str, lang: str) -> str:
    return f"{case_id}:{lang}"


def warm(cases: List[Dict[str, Any]], langs: List[str]) -> None:
    print(f"Warming {len(cases)} cases x {len(langs)} languages...\n")
    warmed: Dict[str, Any] = {}

    for case in cases:
        for lang in langs:
            payload = PredictionPayload.from_dict(case["payload"])
            advisory = generate_advisory(payload, lang=lang, use_cache=False)
            status = "ok" if advisory.generated_by == "llm" else advisory.generated_by
            print(f"  {case['id']:<18} {lang}  {status}")
            if advisory.lang != lang:
                print(f"      !! asked for {lang}, got {advisory.lang}")
            warmed[cache_key(case["id"], lang)] = {
                "headline": advisory.headline,
                "body": advisory.body,
                "sms_text": advisory.sms_text,
                "lang": advisory.lang,
                "generated_by": advisory.generated_by,
                "llm_model": advisory.llm_model,
                "disclaimer": advisory.disclaimer,
                "band": advisory.verdict.band,
            }

    CACHE_FILE.write_text(json.dumps(warmed, indent=2, ensure_ascii=False), "utf-8")
    snapshot = collector.snapshot()
    print(f"\nwrote {CACHE_FILE.relative_to(REPO_ROOT)} ({len(warmed)} entries)")
    print(
        f"generated via: {snapshot['paths']}  "
        f"est. cost ${snapshot['estimated_cost_usd']:.4f}"
    )


def check(cases: List[Dict[str, Any]], langs: List[str]) -> int:
    if not CACHE_FILE.exists():
        print("NO DEMO CACHE. Run --warm while you still have good wifi.")
        return 1

    warmed = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    missing, degraded = [], []
    for case in cases:
        for lang in langs:
            entry = warmed.get(cache_key(case["id"], lang))
            if entry is None:
                missing.append(f"{case['id']}/{lang}")
            elif entry["generated_by"] != "llm":
                degraded.append(f"{case['id']}/{lang} ({entry['generated_by']})")
            elif entry["lang"] != lang:
                degraded.append(f"{case['id']}/{lang} (served {entry['lang']})")

    print(f"Demo cache: {len(warmed)} entries")
    if missing:
        print(f"  MISSING ({len(missing)}): {', '.join(missing)}")
    if degraded:
        print(f"  fell back ({len(degraded)}): {', '.join(degraded)}")
    if not missing and not degraded:
        print("  all cases present and LLM-generated. Ready.")
    return 1 if missing else 0


def show(cases: List[Dict[str, Any]], langs: List[str]) -> None:
    warmed = {}
    if CACHE_FILE.exists():
        warmed = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    else:
        print("(no demo cache — showing live/rules output)\n")

    for case in cases:
        print("=" * 72)
        print(f"{case['id']}  —  {case['story']}")
        print("=" * 72)

        for lang in langs:
            entry = warmed.get(cache_key(case["id"], lang))
            if entry is None:
                payload = PredictionPayload.from_dict(case["payload"])
                advisory = generate_advisory(payload, lang=lang, providers=[])
                entry = {
                    "headline": advisory.headline,
                    "body": advisory.body,
                    "sms_text": advisory.sms_text,
                    "generated_by": advisory.generated_by,
                }

            print(f"\n--- {lang} ({entry['generated_by']}) ---")
            print(entry["headline"])
            print()
            print(entry["body"])
            print(f"\nSMS ({len(entry['sms_text'])} chars): {entry['sms_text']}")
        print()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--warm", action="store_true", help="generate and cache (costs money)"
    )
    ap.add_argument(
        "--check", action="store_true", help="verify the cache before demoing"
    )
    ap.add_argument("--lang", action="append", default=None)
    args = ap.parse_args()

    langs = args.lang or DEMO_LANGS
    cases = load_cases()

    if args.warm:
        warm(cases, langs)
    elif args.check:
        sys.exit(check(cases, langs))
    else:
        show(cases, langs)


if __name__ == "__main__":
    main()
