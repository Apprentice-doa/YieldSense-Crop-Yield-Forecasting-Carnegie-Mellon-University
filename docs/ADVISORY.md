# GenAI Advisory

Turns a yield forecast into a written recommendation the farmer can act on, once
per season, generated automatically at forecast time.

This is the **GenAI Advisory** track from the work plan (D1–D8). It is not the
Chatbot track:

| | GenAI Advisory | Chatbot |
|---|---|---|
| Direction | Push — farmer did not ask | Pull — farmer asks |
| Trigger | A forecast is produced | A message arrives |
| Shape | One structured advisory per field per season | Free-form conversation |
| Owns | Post-harvest planning, resource allocation | Q&A, web search, intents |

The chatbot **reads** the stored advisory as grounding context so the two never
contradict each other.

## The core design rule

> **The rules engine decides. The LLM only narrates.**

Every band, threshold, quantity and figure a farmer sees is computed in
[`src/advisory/rules.py`](../src/advisory/rules.py) from
[`configs/advisory_rules.yaml`](../configs/advisory_rules.yaml). The LLM receives
the finished `Verdict` and may only rephrase and translate it.

This is not stylistic caution. It buys four things at once:

1. **Safety** — the model cannot invent a fertiliser dose or a yield figure,
   because it is never asked to produce one.
2. **Testability** — the engine is pure and dependency-light, so the whole
   decision surface is unit-tested in CI today, with no API key and no network.
3. **Availability** — when the provider is down, `render_rules_advisory()` is
   already a complete, sendable advisory. The farmer always gets something.
4. **Cost** — the SMS path is rendered by rules, so the 2G delivery objective
   costs nothing per message and is byte-for-byte predictable.

## Pipeline

```
ML track                  advisory track                         delivery
────────                  ──────────────                         ────────
PredictionPayload  ──►  build_verdict()  ──►  Verdict  ──┬──►  LLM narrate + translate  ──►  web
                        (deterministic)                  │      (falls back to rules)
                                                         └──►  render_sms()  ──────────────►  2G SMS
```

- [`schemas.py`](../src/advisory/schemas.py) — `PredictionPayload` (ML → us) and
  `Advisory` (us → backend, SMS, chatbot). Field names mirror the dataset
  columns exactly, so there is no mapping layer to get wrong.
- [`rules.py`](../src/advisory/rules.py) — data-quality gates, yield band,
  confidence, driver rules, conflict resolution, post-harvest plan, renderers.
- [`prompts/`](../src/advisory/prompts/) — `system.md` (hard constraints),
  `advisory_user.md` (verdict + permitted numbers), `translate.md`.
- [`providers/`](../src/advisory/providers/) — Gemini and OpenAI over plain HTTP
  (`requests`, no vendor SDKs), plus `FakeProvider` for offline tests.
- [`validation.py`](../src/advisory/validation.py) — shape, numeric fidelity,
  safety and substance checks applied to every generated response.
- [`generator.py`](../src/advisory/generator.py) — the escalation ladder.
- [`cache.py`](../src/advisory/cache.py) — TTL + LRU, keyed on payload hash.
- [`trigger.py`](../src/advisory/trigger.py) — `on_prediction_complete()` and
  sink registration.
- [`api.py`](../src/advisory/api.py) — FastAPI router. Imported explicitly, never
  from the package `__init__`, so the engine stays framework-free.

## Generation cannot fail

`generate_advisory()` escalates and always terminates at something sendable:

```
cache hit                                   -> return
provider 1, attempt 1                       -> validate -> return if clean
provider 1, attempt 2 (repair, with errors) -> validate -> return if clean
provider 2, attempts 1..2                   -> validate -> return if clean
rules-only advisory                         -> always succeeds
```

Every generated response is validated before it can reach a farmer. A failure
does not just get rejected — the specific errors are fed back as a repair hint,
so the second attempt is told exactly which figure was invented or which banned
topic it touched. `generated_by` on the returned `Advisory` records the path
taken (`llm`, `llm_fallback_rules`, `rules`), which is what D5–D6 measures.

Four independent checks in `validation.py`:

| Check | Rejects |
|---|---|
| shape | missing keys, over-length headline or body |
| numeric | any figure not in `Verdict.numeric_facts()` |
| safety | pesticide/fertiliser dosing, financial or legal advice, "five-year average", "guarantee" |
| substance | actions added, dropped, or reordered relative to the verdict |
| band | a below-typical forecast narrated as good news |

**The SMS is never LLM-written**, even when generation succeeds. It stays
rules-rendered: deterministic, free, and exactly within one 160-char segment.

### Cost and failure controls

- `max_llm_calls_per_advisory` (default 4) caps total calls across *all*
  providers and retries, so a fleet of misbehaving providers cannot multiply.
- A non-retryable error (missing API key, 401) does not retry that provider.
- A transient provider outage is **not** cached — otherwise a 30-second blip
  would pin the rules fallback for the 90-day TTL.
- With no key configured at all, providers are skipped without a network call.

### Cache key

`sha256(payload) + rules_version + lang`. Consequences, each tested:

- A revised forecast changes the payload hash → misses cleanly and regenerates.
  No stale advice on a corrected number.
- A rules change bumps `rules_version` → invalidates exactly what it should.
- Each language is cached separately.

Storage is in-process. Redis means implementing `get`/`set` on `AdvisoryCache`;
`REDIS_URL` is already in `.env.example`.

## What the rules engine guarantees

Each of these is enforced by a test in
[`tests/test_advisory_rules.py`](../tests/test_advisory_rules.py):

- **No invented numbers.** Every figure in the prose traces back to
  `Verdict.numeric_facts()`. The same assertion runs against LLM output in the
  D5–D6 eval harness — proving it against the rules renderer first is what makes
  the check itself trustworthy.
- **No advice on bad data.** A rule whose feature is missing or physically
  implausible is *suppressed*, not fired. An NDVI of −1.0 is cloud or water, not
  a struggling crop, and we do not send someone walking their field over it.
- **No contradictions.** Low rainfall and wet soil both fire; only one survives.
  A farmer told to irrigate *and* to hold off has been given nothing. See
  `conflicts` in the rules config.
- **No invented quantities.** Storage, labour and volume require `area_ha`. With
  no area we give qualitative guidance and omit the numbers rather than guess.
- **Degradation over guessing.** An unknown crop yields band `unknown`, no
  baseline ratio, and no drying estimate — but still gets post-harvest guidance.
- **One SMS segment.** ≤160 characters, cut on a word boundary.
- **Deterministic.** Same payload, same verdict, always. This is what makes the
  cache key sound.

## Known limits of the data

These are properties of `data/external/yield_prediction_dataset.csv`, and they
constrain what the advisory is allowed to claim.

- **No historical baseline exists.** The data is one season (2023-01 to 2023-05,
  25 fortnightly dates, 90 fields). The "typical" yield is a *within-dataset
  crop mean*, generated by
  [`scripts/build_crop_baselines.py`](../scripts/build_crop_baselines.py).
  Advisory copy says "typical in our records" and must never say "your five-year
  average" or "the district average" — enforced in `system.md`.
- **The dataset is not African and is likely synthetic.** Coordinates are
  ~22.6°N, 88.5°E (West Bengal, India). All 30 crops have near-identical yield
  distributions (Coconut 45.6 ± 1.8 vs Wheat 41.7 ± 7.3), which real agronomy
  does not produce. Rainfall alone correlates 0.756 with yield.
- **`NDWI` is discarded.** It is an exact negation of `GNDVI` (r = −1.0) and
  carries no additional information.
- **`yield` has no units.** Carried as `yield_unit` on the payload and echoed
  verbatim; the default placeholder is `units/ha`.

None of this blocks the track — the engine is data-agnostic and the configs are
regenerated by script. It does mean the advisory is a *relative, within-season*
signal, and it is written to sound like one.

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| 1 | What are the units of `yield`? | Data & ML | Post-harvest quantities being meaningful |
| 2 | Is a real African dataset available, or do we state the limitation in the report? | Team | What the advisory may claim |
| 3 | Does the payload carry `area_ha`, and from where? | Platform | Post-harvest quantities existing at all |
| 4 | Confirm Kinyarwanda / Kiswahili / French reviewers for D5–D6 | Team | Multilingual sign-off |

Settled: the advisory fires **once per season**, at forecast time. The cache key
(`payload hash + rules_version + lang`) still supports re-running it if a
forecast is revised.

## Running it

```bash
python scripts/build_crop_baselines.py     # -> configs/crop_baselines.yaml
python scripts/build_advisory_fixtures.py  # -> tests/fixtures/advisory/*.json
pytest tests/test_advisory_rules.py tests/test_advisory_generator.py \
       tests/test_advisory_trigger.py tests/test_advisory_api.py --no-cov
```

The whole suite runs offline. No API key is needed and none is used — provider
behaviour is scripted with `FakeProvider`, which is how failure modes we cannot
trigger reliably against a live API (timeouts, malformed JSON, invented figures,
banned topics) are covered at all.

### Wiring into the app

```python
from src.advisory.api import router as advisory_router
app.include_router(advisory_router)
```

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/advisory` | Full advisory for one forecast |
| `POST /api/v1/advisory/sms` | 160-char version only — costs no LLM call |
| `GET /api/v1/advisory/health` | Readiness, live providers, cache stats |

### Wiring the trigger

```python
from src.advisory.trigger import register_sink, on_prediction_complete

register_sink(save_advisory_to_db)
register_sink(queue_sms)

on_prediction_complete(prediction_dict)   # once per season, at forecast time
```

A failing sink is logged and skipped — one broken downstream service must not
lose the advisory for the others.

### Configuring providers

Set `GEMINI_API_KEY` and/or `OPENAI_API_KEY`. Both optional: with neither, the
service still runs and serves rules-only text. Model choice and timeouts live in
[`configs/advisory_llm.yaml`](../configs/advisory_llm.yaml), kept separate from
the rules config so swapping a model does not invalidate the cache.

Bump `rules_version` in `configs/advisory_rules.yaml` on **any** threshold
change — it is part of the cache key and is stamped on every advisory.

## Status against the work plan

- **D1–D2 Scope prompts & advisory rules** — done: rules table, both contracts,
  prompt templates, 10 fixtures.
- **D3–D4 Build & trigger LLM** — done: Gemini + OpenAI adapters, validation with
  repair retry, rules fallback, cache, `POST /api/v1/advisory`, `/sms`,
  `/health`, on-prediction-complete trigger with sinks. 143 tests passing.
- **D5–D6 Test on real predictions** — next: golden set of 20–30 real forecasts
  from the ML track, eval harness (numeric fidelity, schema validity, rule
  coverage, latency, cost per 1000, `generated_by` mix), live-provider smoke
  test, native-speaker review of the four languages.
- **D7–D8 QA & polish** — red-team prompts, season performance report,
  observability, demo script with pre-cached farms.

### Not yet built, deliberately

- **Translation is not wired in.** `translate.md` exists and the generator asks
  for the target language directly, but the separate translate-then-verify pass
  belongs with the native-speaker review in D5–D6. Until then, treat non-English
  output as untested.
- **No live-provider test.** Everything is `FakeProvider`. The first real call
  should be a D5–D6 smoke test with a budget cap.
- **Cache is in-process.** Fine for the demo, wrong for multiple workers.
