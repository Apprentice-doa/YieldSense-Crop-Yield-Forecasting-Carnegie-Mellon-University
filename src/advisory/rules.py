"""Deterministic advisory rules engine.

Rules decide, the LLM narrates. This module contains zero LLM calls and zero
network access, so it runs in CI, is fully unit-testable, and doubles as the
fallback path when the LLM provider is unavailable.

    payload (from the ML track) -> Verdict (every number the farmer will see)

Thresholds live in configs/advisory_rules.yaml; baselines in
configs/crop_baselines.yaml. Neither is hard-coded here.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .schemas import Action, Advisory, PostHarvestPlan, PredictionPayload, Verdict

REPO_ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = REPO_ROOT / "configs" / "advisory_rules.yaml"
BASELINES_PATH = REPO_ROOT / "configs" / "crop_baselines.yaml"


@functools.lru_cache(maxsize=4)
def load_config(
    rules_path: str = str(RULES_PATH), baselines_path: str = str(BASELINES_PATH)
) -> tuple:
    with open(rules_path, encoding="utf-8") as fh:
        rules = yaml.safe_load(fh)
    with open(baselines_path, encoding="utf-8") as fh:
        baselines = yaml.safe_load(fh)
    return rules, baselines


# --------------------------------------------------------------------------- #
# Data quality
# --------------------------------------------------------------------------- #
def check_data_quality(payload: PredictionPayload, rules: Dict[str, Any]) -> List[str]:
    """Return a flag per feature that is missing or physically implausible.

    A flagged feature is not merely noted -- rules that depend on it are
    suppressed, so we never advise a farmer to scout a field on the basis of an
    NDVI of -1.0 (cloud or water, not a crop).
    """
    flags: List[str] = []
    for feat, bounds in rules["data_quality"].items():
        value = getattr(payload, feat, None)
        if value is None:
            flags.append(f"{feat}:missing")
            continue
        if not (bounds["min"] <= value <= bounds["max"]):
            flags.append(f"{feat}:out_of_range")
            continue
        valid_min = bounds.get("valid_min")
        if valid_min is not None and value < valid_min:
            flags.append(f"{feat}:implausible")
    return flags


def _feature_usable(feat: str, flags: List[str]) -> bool:
    return not any(f.startswith(f"{feat}:") for f in flags)


# --------------------------------------------------------------------------- #
# Yield band and confidence
# --------------------------------------------------------------------------- #
def classify_band(ratio: Optional[float], rules: Dict[str, Any]) -> tuple:
    if ratio is None:
        return "unknown", "No baseline available for this crop", "none"
    for band in rules["yield_bands"]:
        lo = band.get("min_ratio")
        hi = band.get("max_ratio")
        if (lo is None or ratio >= lo) and (hi is None or ratio < hi):
            return band["id"], band["label"], band["severity"]
    return "unknown", "No baseline available for this crop", "none"


def classify_confidence(
    predicted: float, interval: Optional[List[float]], rules: Dict[str, Any]
) -> str:
    if not interval or len(interval) != 2 or predicted <= 0:
        return "unknown"
    lo, hi = sorted(interval)
    width = (hi - lo) / predicted
    cfg = rules["confidence"]
    if width <= cfg["high_max_width"]:
        return "high"
    if width <= cfg["medium_max_width"]:
        return "medium"
    return "low"


# --------------------------------------------------------------------------- #
# Driver rules
# --------------------------------------------------------------------------- #
def _threshold(rule: Dict[str, Any], baselines: Dict[str, Any]) -> Optional[float]:
    if "absolute" in rule:
        return float(rule["absolute"])
    pct = baselines["features"].get(rule["feature"], {}).get(rule["percentile"])
    return None if pct is None else float(pct)


def resolve_conflicts(fired_ids: List[str], rules: Dict[str, Any]) -> List[str]:
    """Drop rules that contradict a rule we trust more. Returns dropped ids."""
    dropped: List[str] = []
    active = set(fired_ids)
    for conflict in rules.get("conflicts", []):
        group = set(conflict["when_all"])
        if group.issubset(active):
            losers = group - {conflict["keep"]}
            dropped.extend(sorted(losers))
            active -= losers
    return dropped


def evaluate_drivers(
    payload: PredictionPayload,
    rules: Dict[str, Any],
    baselines: Dict[str, Any],
    flags: List[str],
) -> tuple:
    """Fire every driver rule whose feature is usable. Returns (actions, drivers, suppressed)."""
    suppressed: List[str] = []
    fired: List[Dict[str, Any]] = []

    for rule in rules["drivers"]:
        feat = rule["feature"]
        needed = set(rule.get("requires_valid", [])) | {feat}
        if not all(_feature_usable(f, flags) for f in needed):
            suppressed.append(rule["id"])
            continue

        value = getattr(payload, feat)
        threshold = _threshold(rule, baselines)
        if threshold is None:
            suppressed.append(rule["id"])
            continue

        fired_now = value < threshold if rule["op"] == "lt" else value > threshold
        if fired_now:
            fired.append(rule)

    dropped = resolve_conflicts([r["id"] for r in fired], rules)
    suppressed.extend(dropped)
    fired = [r for r in fired if r["id"] not in dropped]

    actions = [
        Action(
            rule_id=rule["id"],
            action=rule["action"],
            why=rule["driver"],
            urgency=rule["urgency"],
            severity=rule["severity"],
            stage="in_season",
            sms_action=rule.get("sms_action"),
        )
        for rule in fired
    ]
    drivers = [rule["driver"] for rule in fired]

    # A healthy field still deserves a straight answer rather than silence.
    if not actions and "all_clear" in rules:
        cfg = rules["all_clear"]
        actions.append(
            Action(
                rule_id="all_clear",
                action=cfg["action"],
                why=cfg["driver"],
                urgency=cfg["urgency"],
                severity=cfg["severity"],
                stage="in_season",
                sms_action=cfg.get("sms_action"),
            )
        )
        drivers.append(cfg["driver"])

    return actions, drivers, suppressed


# --------------------------------------------------------------------------- #
# Post-harvest planning
# --------------------------------------------------------------------------- #
def build_post_harvest(
    payload: PredictionPayload, band: str, rules: Dict[str, Any]
) -> PostHarvestPlan:
    cfg = rules["post_harvest"]
    note = cfg["market_note_by_band"].get(band, cfg["market_note_by_band"]["on_track"])
    plan = PostHarvestPlan(market_note=note)

    # Drying time scales with expected volume, which we only know relative to a
    # baseline. With an unknown band we leave it unset rather than guess.
    drying = cfg["drying_days_per_band"].get(band)
    if drying is not None:
        plan.drying_days = int(drying)

    # Quantities need an area. We never invent one.
    if payload.area_ha and payload.area_ha > 0:
        volume = payload.predicted_yield * payload.area_ha
        plan.expected_volume = round(volume, 2)
        plan.volume_unit = payload.yield_unit.replace("/ha", "")
        plan.storage_capacity_needed = round(volume * cfg["storage_headroom"], 2)
        plan.labour_days = round(payload.area_ha * cfg["labour_days_per_ha"], 1)

    return plan


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def build_verdict(
    payload: PredictionPayload, config: Optional[tuple] = None
) -> Verdict:
    """payload -> Verdict. Pure, deterministic, no I/O beyond config load."""
    rules, baselines = config or load_config()

    # Sanitisation flags travel with the data-quality flags so an injection
    # attempt shows up in logs and in the API response, not just in a variable.
    flags = check_data_quality(payload, rules) + list(payload.input_flags)

    crop = baselines["crops"].get(payload.crop_type)
    baseline_yield = float(crop["mean"]) if crop else None
    ratio = (
        round(payload.predicted_yield / baseline_yield, 3) if baseline_yield else None
    )

    band, band_label, band_severity = classify_band(ratio, rules)
    confidence = classify_confidence(
        payload.predicted_yield, payload.prediction_interval, rules
    )

    actions, drivers, suppressed = evaluate_drivers(payload, rules, baselines, flags)

    # The band itself is a driver worth stating, and a low band earns its own action.
    if band in ("critical", "below"):
        drivers.insert(
            0,
            f"Predicted yield is {ratio:.0%} of the typical {payload.crop_type} "
            f"yield in our records",
        )
        actions.append(
            Action(
                rule_id=f"band_{band}",
                action=(
                    "Plan for a smaller harvest than usual: hold back enough of the "
                    "crop for household needs before committing any of it to sale"
                ),
                why=f"{band_label} predicted yield for this crop",
                urgency="soon" if band == "critical" else "routine",
                severity=band_severity,
                stage="post_harvest",
            )
        )

    if confidence == "low":
        drivers.append(
            "The model's estimate for this field has a wide range, so treat it as "
            "a rough guide"
        )

    actions.sort(key=lambda a: a.sort_key())
    actions = actions[: rules["delivery"]["max_actions_in_full"]]

    post_harvest = build_post_harvest(payload, band, rules)
    actions.append(
        Action(
            rule_id="post_harvest_market",
            action=post_harvest.market_note,
            why="Post-harvest planning based on expected volume",
            urgency="routine",
            severity="none",
            stage="post_harvest",
        )
    )

    return Verdict(
        field_id=payload.field_id,
        crop_type=payload.crop_type,
        predicted_yield=round(payload.predicted_yield, 2),
        yield_unit=payload.yield_unit,
        baseline_yield=baseline_yield,
        baseline_ratio=ratio,
        band=band,
        band_label=band_label,
        confidence=confidence,
        prediction_interval=payload.prediction_interval,
        drivers=drivers,
        actions=actions,
        post_harvest=post_harvest,
        suppressed_rules=suppressed,
        data_quality_flags=flags,
        rules_version=rules["rules_version"],
        baseline_caveat=baselines["_caveat"],
    )


# --------------------------------------------------------------------------- #
# Rules-only rendering (the fallback path, and the SMS path always)
# --------------------------------------------------------------------------- #
I18N_PATH = REPO_ROOT / "configs" / "advisory_i18n.yaml"


@functools.lru_cache(maxsize=2)
def load_i18n(path: str = str(I18N_PATH)) -> Dict[str, Any]:
    """Reviewed SMS translations, or an empty map if the file is absent.

    SMS strings are translated at build time, not per message: there are only
    ~14 short strings per language, so a native speaker can review one small
    file instead of hundreds of messages, and the 2G path stays deterministic
    and free.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except FileNotFoundError:
        return {}


def strings_for(lang: str) -> Dict[str, Any]:
    """Translations for one language, empty if unavailable."""
    if lang == "en":
        return {}
    return (load_i18n().get("languages") or {}).get(lang) or {}


def render_sms(verdict: Verdict, rules: Dict[str, Any], lang: str = "en") -> str:
    """Deterministic <=160 char SMS. Never LLM-generated: it must be free and exact.

    Falls back to English string by string, so a partially translated language
    still sends a usable message rather than a blank one.
    """
    limit = rules["delivery"]["sms_max_chars"]
    strings = strings_for(lang)

    top = next((a for a in verdict.actions if a.stage == "in_season"), None)
    if top is None:
        top = verdict.actions[0] if verdict.actions else None

    band_label = (strings.get("band_labels") or {}).get(
        verdict.band, verdict.band_label
    )
    head = (
        f"{verdict.crop_type} {verdict.field_id}: "
        f"~{verdict.predicted_yield:g} {verdict.yield_unit} ({band_label})."
    )
    if top is None:
        return head[:limit]

    remaining = limit - len(head) - 1
    if remaining <= 12:
        return head[:limit]

    # Prefer the authored short form. Truncating the full action loses part of
    # the instruction, and on 2G the SMS is the whole advisory.
    tail = (strings.get("sms_actions") or {}).get(top.rule_id) or (
        top.sms_action or top.action
    )
    if len(tail) > remaining:
        # Cut on a word boundary: "...note which pa." is worse than a short
        # sentence, and this is the only text some farmers ever see.
        cut = tail[:remaining]
        if " " in cut:
            cut = cut[: cut.rindex(" ")]
        tail = cut.rstrip(" ,;:-") + "."
    return f"{head} {tail}"[:limit]


def render_rules_advisory(verdict: Verdict, rules: Dict[str, Any]) -> Advisory:
    """Full advisory with no LLM involved.

    This is what a farmer receives when the provider is down or the generated
    text fails validation, so it has to stand on its own.
    """
    headline = (
        f"{verdict.crop_type} on {verdict.field_id}: "
        f"{verdict.band_label.lower()} this season"
    )

    lines = [
        f"Estimated yield: {verdict.predicted_yield:g} {verdict.yield_unit}"
        + (
            f" (range {verdict.prediction_interval[0]:g}-"
            f"{verdict.prediction_interval[1]:g})"
            if verdict.prediction_interval
            else ""
        )
        + "."
    ]
    if verdict.baseline_yield is not None:
        lines.append(
            f"Typical for {verdict.crop_type} in our records: "
            f"{verdict.baseline_yield:g} {verdict.yield_unit}."
        )
    if verdict.drivers:
        lines.append("")
        lines.append("Why:")
        lines.extend(f"- {d}" for d in verdict.drivers)

    lines.append("")
    lines.append("What to do:")
    lines.extend(f"- {a.action}" for a in verdict.actions)

    ph = verdict.post_harvest
    if ph and ph.expected_volume is not None:
        # Assemble from the parts we actually have: an unknown band leaves
        # drying_days unset, and "roughly None drying days" must never ship.
        parts = [f"storage for {ph.storage_capacity_needed:g}"]
        if ph.drying_days is not None:
            parts.append(f"roughly {ph.drying_days} drying days")
        if ph.labour_days is not None:
            parts.append(f"{ph.labour_days:g} labour-days")
        lines.append("")
        lines.append(
            f"Plan for about {ph.expected_volume:g} {ph.volume_unit} at harvest "
            f"({', '.join(parts)})."
        )

    return Advisory(
        field_id=verdict.field_id,
        lang="en",
        headline=headline,
        body="\n".join(lines),
        sms_text=render_sms(verdict, rules),
        verdict=verdict,
        disclaimer=rules["safety"]["disclaimer"],
        generated_by="rules",
    )


def advise(payload: PredictionPayload) -> Advisory:
    """Convenience entry point: payload -> rules-only Advisory."""
    rules, baselines = load_config()
    verdict = build_verdict(payload, (rules, baselines))
    return render_rules_advisory(verdict, rules)
