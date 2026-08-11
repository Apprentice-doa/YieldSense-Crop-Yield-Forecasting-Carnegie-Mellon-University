"""End-of-season performance report.

The problem statement promises farmers can "generate performance reports". This
is that: once the harvest is in, compare what we predicted against what actually
happened, and say plainly whether the forecast was any good.

Deliberately blunt about our own accuracy. A tool that quietly forgets its worse
predictions is not one a farmer should trust with next season's planning, and an
honest miss is more useful to them than a flattering summary -- it tells them how
much weight to put on the next forecast.

Like the advisory itself, every number here is computed, never generated.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .rules import build_verdict, load_config
from .schemas import PredictionPayload

# How close a forecast has to be before we call it accurate. 10% is the band
# within which a farmer's storage and labour planning would not have changed.
ACCURATE_WITHIN = 0.10
FAIR_WITHIN = 0.25


@dataclass
class FieldOutcome:
    """One field's forecast against its actual harvest."""

    field_id: str
    crop_type: str
    predicted: float
    actual: float
    unit: str
    baseline: Optional[float] = None
    predicted_band: str = "unknown"
    actual_band: str = "unknown"

    @property
    def error(self) -> float:
        return self.actual - self.predicted

    @property
    def error_pct(self) -> Optional[float]:
        if self.actual == 0:
            return None
        return round(100 * self.error / self.actual, 1)

    @property
    def accuracy_label(self) -> str:
        if self.error_pct is None:
            return "unknown"
        magnitude = abs(self.error_pct) / 100
        if magnitude <= ACCURATE_WITHIN:
            return "accurate"
        if magnitude <= FAIR_WITHIN:
            return "close"
        return "off"

    @property
    def band_was_right(self) -> bool:
        """Did we get the *decision* right, even if the number was off?

        This matters more than the raw error. A farmer acts on "below typical",
        not on the third decimal place -- a 15% error that still lands in the
        right band changed none of their decisions.
        """
        return self.predicted_band == self.actual_band

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data.update(
            error=round(self.error, 2),
            error_pct=self.error_pct,
            accuracy_label=self.accuracy_label,
            band_was_right=self.band_was_right,
        )
        return data


@dataclass
class SeasonReport:
    season: str
    outcomes: List[FieldOutcome] = field(default_factory=list)

    @property
    def fields(self) -> int:
        return len(self.outcomes)

    @property
    def mean_absolute_error_pct(self) -> Optional[float]:
        errors = [abs(o.error_pct) for o in self.outcomes if o.error_pct is not None]
        return round(sum(errors) / len(errors), 1) if errors else None

    @property
    def bias_pct(self) -> Optional[float]:
        """Signed, so systematic over- or under-forecasting is visible.

        A mean absolute error hides this: consistently over-predicting by 12%
        looks identical to random noise unless you keep the sign.
        """
        errors = [o.error_pct for o in self.outcomes if o.error_pct is not None]
        return round(sum(errors) / len(errors), 1) if errors else None

    @property
    def band_accuracy(self) -> Optional[float]:
        if not self.outcomes:
            return None
        return round(
            100 * sum(o.band_was_right for o in self.outcomes) / len(self.outcomes), 1
        )

    def counts(self) -> Dict[str, int]:
        out: Dict[str, int] = {"accurate": 0, "close": 0, "off": 0, "unknown": 0}
        for outcome in self.outcomes:
            out[outcome.accuracy_label] += 1
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {
            "season": self.season,
            "fields": self.fields,
            "mean_absolute_error_pct": self.mean_absolute_error_pct,
            "bias_pct": self.bias_pct,
            "band_accuracy_pct": self.band_accuracy,
            "counts": self.counts(),
            "outcomes": [o.to_dict() for o in self.outcomes],
        }

    # -- rendering ---------------------------------------------------------- #
    def to_text(self) -> str:
        """Plain text a farmer or an extension officer can read."""
        if not self.outcomes:
            return f"Season {self.season}: no harvest results recorded yet."

        lines = [
            f"Season {self.season} — how our forecasts performed",
            "=" * 52,
            "",
            f"Fields with recorded harvests: {self.fields}",
        ]

        counts = self.counts()
        lines.append(
            f"Within 10% of the real harvest: {counts['accurate']} of {self.fields}"
        )
        if self.mean_absolute_error_pct is not None:
            lines.append(f"Average error: {self.mean_absolute_error_pct}%")
        if self.bias_pct is not None:
            direction = "over" if self.bias_pct < 0 else "under"
            lines.append(
                f"On average we {direction}-estimated by " f"{abs(self.bias_pct)}%"
                if abs(self.bias_pct) >= 1
                else "No consistent over- or under-estimation."
            )
        if self.band_accuracy is not None:
            lines.append(
                f"We correctly said whether the season would be above or below "
                f"typical for {self.band_accuracy}% of fields."
            )

        lines += ["", "Field by field:", ""]
        for o in sorted(
            self.outcomes, key=lambda x: abs(x.error_pct or 0), reverse=True
        ):
            mark = {"accurate": "ok", "close": "~", "off": "MISSED"}.get(
                o.accuracy_label, "?"
            )
            lines.append(
                f"  [{mark:>6}] {o.field_id} ({o.crop_type}): "
                f"predicted {o.predicted:g}, actual {o.actual:g} {o.unit}"
                + (f", {o.error_pct:+.1f}%" if o.error_pct is not None else "")
            )

        worst = max(
            (o for o in self.outcomes if o.error_pct is not None),
            key=lambda o: abs(o.error_pct),
            default=None,
        )
        if worst and abs(worst.error_pct) > FAIR_WITHIN * 100:
            lines += [
                "",
                f"Our worst miss was {worst.field_id} ({worst.crop_type}), off by "
                f"{abs(worst.error_pct):.0f}%. Treat next season's estimate for "
                f"this field with extra caution.",
            ]

        lines += [
            "",
            "These figures cover our forecasts only. They are not a measure of "
            "your farming.",
        ]
        return "\n".join(lines)


def build_season_report(
    records: List[Dict[str, Any]], season: str = "current"
) -> SeasonReport:
    """Build a report from records carrying both a prediction and an actual yield.

    Each record is a prediction payload plus `actual_yield`. Records without one
    are skipped rather than assumed: a missing harvest figure is not a zero.
    """
    _, baselines = load_config()
    report = SeasonReport(season=season)

    for record in records:
        actual = record.get("actual_yield")
        if actual is None:
            continue

        payload = PredictionPayload.from_dict(record)
        predicted_verdict = build_verdict(payload)

        # Re-run the same banding on the actual yield, so "did we get the
        # decision right" is judged by identical rules.
        actual_payload = PredictionPayload.from_dict(
            {**record, "predicted_yield": float(actual)}
        )
        actual_verdict = build_verdict(actual_payload)

        crop = baselines["crops"].get(payload.crop_type)
        report.outcomes.append(
            FieldOutcome(
                field_id=payload.field_id,
                crop_type=payload.crop_type,
                predicted=round(payload.predicted_yield, 2),
                actual=round(float(actual), 2),
                unit=payload.yield_unit,
                baseline=float(crop["mean"]) if crop else None,
                predicted_band=predicted_verdict.band,
                actual_band=actual_verdict.band,
            )
        )

    return report
