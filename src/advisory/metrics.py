"""Per-advisory metrics.

Motivated by a real incident. The live eval quietly dropped 3% of advisories to
the rules fallback because our own numeric check was too strict. Nothing was
wrong with the output, so nothing alerted -- an over-strict validator fails
safely and silently, and you simply serve worse advisories until someone reads a
report. The only reason it surfaced was that the eval prints the `generated_by`
mix.

So the same signal is emitted in production. What matters is not that a request
succeeded -- it always does, by design -- but *which path* it took and *why*.

Emitted as a single structured log line per advisory, and aggregated in-process
so `GET /api/v1/advisory/health` can report the mix without a metrics backend.
Swap in Prometheus or OpenTelemetry by reimplementing `record()`.
"""

from __future__ import annotations

import json
import math
import logging
import threading
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("advisory.metrics")

# ~4 characters per token, and USD per 1M tokens for the configured small
# models. An order-of-magnitude figure for spotting runaway cost, not billing.
CHARS_PER_TOKEN = 4
COST_PER_1M_INPUT = 0.15
COST_PER_1M_OUTPUT = 0.60


@dataclass
class AdvisoryMetrics:
    """One advisory's worth of operational facts."""

    field_id: str
    crop_type: str
    lang: str
    band: str
    confidence: str
    generated_by: str
    rules_version: str
    schema_version: str

    llm_model: Optional[str] = None
    model_version: Optional[str] = None
    latency_ms: float = 0.0
    llm_calls: int = 0
    translated: bool = False
    cache_hit: bool = False

    prompt_chars: int = 0
    output_chars: int = 0

    # Why an advisory took the path it did. Empty on the happy path.
    validation_failures: List[str] = field(default_factory=list)
    provider_failures: List[str] = field(default_factory=list)
    data_quality_flags: List[str] = field(default_factory=list)

    @property
    def degraded(self) -> bool:
        return self.generated_by != "llm"

    @property
    def estimated_cost_usd(self) -> float:
        in_tokens = self.prompt_chars / CHARS_PER_TOKEN
        out_tokens = self.output_chars / CHARS_PER_TOKEN
        return (
            in_tokens * COST_PER_1M_INPUT + out_tokens * COST_PER_1M_OUTPUT
        ) / 1_000_000

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["degraded"] = self.degraded
        data["estimated_cost_usd"] = round(self.estimated_cost_usd, 6)
        return data


class MetricsCollector:
    """In-process aggregation. Thread-safe, bounded, no external dependency."""

    def __init__(self, keep_recent: int = 200):
        self._lock = threading.Lock()
        self._counts: Counter = Counter()
        self._latencies: List[float] = []
        self._recent: List[Dict[str, Any]] = []
        self._cost = 0.0
        self._keep_recent = keep_recent
        self._injection_attempts = 0

    def record(self, metrics: AdvisoryMetrics) -> None:
        # One structured line per advisory: greppable, and parseable by whatever
        # log pipeline the platform track ends up using.
        logger.info("advisory_generated %s", json.dumps(metrics.to_dict(), default=str))

        with self._lock:
            self._counts["total"] += 1
            self._counts[f"path.{metrics.generated_by}"] += 1
            self._counts[f"band.{metrics.band}"] += 1
            self._counts[f"lang.{metrics.lang}"] += 1
            if metrics.cache_hit:
                self._counts["cache_hit"] += 1
            if metrics.degraded:
                self._counts["degraded"] += 1
            if metrics.translated:
                self._counts["translated"] += 1
            if any("injection_attempt" in f for f in metrics.data_quality_flags):
                self._injection_attempts += 1

            self._counts["llm_calls"] += metrics.llm_calls
            self._cost += metrics.estimated_cost_usd

            if not metrics.cache_hit:
                self._latencies.append(metrics.latency_ms)
                if len(self._latencies) > 1000:
                    self._latencies = self._latencies[-1000:]

            self._recent.append(metrics.to_dict())
            if len(self._recent) > self._keep_recent:
                self._recent = self._recent[-self._keep_recent :]

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            total = self._counts["total"]
            latencies = sorted(self._latencies)

            def pct(p: float) -> Optional[float]:
                """Nearest-rank percentile.

                Deliberately not floor-interpolated: on small samples that
                rounds the tail away (p95 of five values would report the
                fourth), and the tail is the entire point of a p95.
                """
                if not latencies:
                    return None
                rank = math.ceil(p * len(latencies))
                return round(latencies[min(max(rank - 1, 0), len(latencies) - 1)], 1)

            return {
                "total": total,
                "paths": {
                    k.split(".", 1)[1]: v
                    for k, v in self._counts.items()
                    if k.startswith("path.")
                },
                # The number to watch. A rising degraded rate means the LLM path
                # is failing, or a validator has become too strict.
                "degraded_rate": (
                    round(self._counts["degraded"] / total, 4) if total else None
                ),
                "cache_hit_rate": (
                    round(self._counts["cache_hit"] / total, 4) if total else None
                ),
                "translated": self._counts["translated"],
                "llm_calls": self._counts["llm_calls"],
                "estimated_cost_usd": round(self._cost, 4),
                "latency_ms": {"p50": pct(0.5), "p95": pct(0.95)},
                "bands": {
                    k.split(".", 1)[1]: v
                    for k, v in self._counts.items()
                    if k.startswith("band.")
                },
                "injection_attempts": self._injection_attempts,
            }

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return self._recent[-limit:]

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()
            self._latencies.clear()
            self._recent.clear()
            self._cost = 0.0
            self._injection_attempts = 0


# Process-wide collector.
collector = MetricsCollector()
