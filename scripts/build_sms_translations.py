"""Translate the SMS strings once, into a file a native speaker can review.

SMS strings are not translated per message. There are only ~14 short strings per
language, and translating them at runtime would mean paying for every SMS,
risking a bad translation on the one channel where the farmer sees nothing else,
and giving reviewers hundreds of near-identical messages to check.

Translating them once produces a small file a native speaker can read in a few
minutes, mark reviewed, and correct by hand. After that the 2G path is free,
deterministic, and human-approved.

    python scripts/build_sms_translations.py            # all configured languages
    python scripts/build_sms_translations.py --lang sw  # just one

Writes configs/advisory_sms_i18n.yaml. Machine output starts as
`review_status: unreviewed`; a reviewer sets it to `reviewed` and adds their
name. Nothing in the pipeline blocks on that flag -- it exists so the report can
state honestly which languages a human has actually checked.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

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

from src.advisory.generator import LANGUAGE_NAMES, load_llm_config  # noqa: E402
from src.advisory.providers import build_provider, has_credentials  # noqa: E402
from src.advisory.rules import load_config  # noqa: E402

OUT = REPO_ROOT / "configs" / "advisory_i18n.yaml"

SYSTEM = (
    "You translate short agricultural SMS messages for smallholder farmers. "
    "You return JSON only."
)

INSTRUCTIONS = """Translate each value below into {language_name} (`{lang}`).

These are SMS messages sent to smallholder farmers over 2G. For many of them
this is the only form of the advisory they will ever see, so the translation
must be an instruction they can act on, not a literal word-for-word rendering.

Rules:
1. Keep every message SHORT -- at most {max_chars} characters. Shorter is better.
2. Use the words a farmer in the region actually uses for farm operations,
   irrigation, and crop problems. Not textbook or academic vocabulary.
3. Keep the instruction exact. A softened or generalised translation is a
   failure: "irrigate within a few days" must not become "look after the crop".
4. `band_labels` describe how the harvest compares to a typical one. Keep them
   very short -- they appear in brackets inside the message.
5. Return the SAME JSON structure with the same keys. Translate values only.
6. No transliteration of English words where a real local term exists.

Input:

```json
{payload}
```

Return only the translated JSON object."""


def source_strings(rules: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "band_labels": {
            **{b["id"]: b["label"] for b in rules["yield_bands"]},
            "unknown": "No baseline available for this crop",
        },
        "sms_actions": {
            **{r["id"]: r["sms_action"] for r in rules["drivers"]},
            "all_clear": rules["all_clear"]["sms_action"],
        },
        # Fixed UI microcopy. Without this the web advisory shows an English
        # section heading above Kinyarwanda body text.
        "ui_strings": {"what_to_do": "What to do:"},
    }


def check(translated: Dict[str, Any], source: Dict[str, Any], lang: str) -> list:
    """Structure must survive translation, or the config silently loses strings."""
    problems = []
    for section, entries in source.items():
        got = translated.get(section)
        if not isinstance(got, dict):
            problems.append(f"{lang}: section '{section}' missing or not an object")
            continue
        for key in entries:
            value = got.get(key)
            if not isinstance(value, str) or not value.strip():
                problems.append(f"{lang}: '{section}.{key}' missing or empty")
            elif value.strip() == entries[key].strip():
                problems.append(f"{lang}: '{section}.{key}' was not translated")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", action="append", default=None)
    ap.add_argument("--max-chars", type=int, default=90)
    args = ap.parse_args()

    rules, _ = load_config()
    llm_config = load_llm_config()

    provider = None
    for block in llm_config["providers"]:
        if has_credentials(block):
            provider = build_provider(block, llm_config["generation"])
            break
    if provider is None:
        print("No provider credentials found. Set a key in .env first.")
        sys.exit(1)
    print(f"using {provider.name}:{provider.model}")

    languages = args.lang or [
        lang for lang in rules["delivery"]["languages"] if lang != "en"
    ]
    source = source_strings(rules)

    existing = {}
    if OUT.exists():
        existing = yaml.safe_load(OUT.read_text(encoding="utf-8")) or {}
    out_languages = dict((existing.get("languages") or {}))

    for lang in languages:
        prior = out_languages.get(lang) or {}
        if prior.get("review_status") == "reviewed":
            print(f"  {lang}: already reviewed by a human -- not overwriting")
            continue

        print(
            f"  {lang}: translating {sum(len(v) for v in source.values())} strings..."
        )
        response = provider.generate_json(
            SYSTEM,
            INSTRUCTIONS.format(
                language_name=LANGUAGE_NAMES.get(lang, lang),
                lang=lang,
                max_chars=args.max_chars,
                payload=json.dumps(source, indent=2, ensure_ascii=False),
            ),
        )
        problems = check(response, source, lang)
        for problem in problems:
            print(f"    !! {problem}")

        too_long = {
            k: len(v)
            for k, v in (response.get("sms_actions") or {}).items()
            if isinstance(v, str) and len(v) > args.max_chars
        }
        for key, length in too_long.items():
            print(f"    !! sms_actions.{key} is {length} chars (max {args.max_chars})")

        out_languages[lang] = {
            "name": LANGUAGE_NAMES.get(lang, lang),
            "review_status": "unreviewed",
            "reviewed_by": "",
            "machine_translated_by": f"{provider.name}:{provider.model}",
            "band_labels": response.get("band_labels", {}),
            "sms_actions": response.get("sms_actions", {}),
            "ui_strings": response.get("ui_strings", {}),
        }

    doc = {
        "_generated_by": "scripts/build_sms_translations.py",
        "_note": (
            "Machine translation, pending native-speaker review. Set "
            "review_status to 'reviewed' and fill in reviewed_by once checked. "
            "Hand edits are preserved: a reviewed language is never overwritten."
        ),
        "_source_of_truth": "configs/advisory_rules.yaml (English)",
        "languages": out_languages,
    }
    OUT.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    print(f"\nwrote {OUT.relative_to(REPO_ROOT)}")
    print("Next: a native speaker reviews each language and sets review_status.")


if __name__ == "__main__":
    main()
