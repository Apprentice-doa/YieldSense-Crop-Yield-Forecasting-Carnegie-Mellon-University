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

## D5–D6: what running it at scale found

`scripts/advisory_coverage_report.py` runs the engine over all 1,625 rows.
The advisory consumes a predicted yield; whether that number came from a trained
model or from the dataset's recorded yield does not change whether the resulting
advisory is well-formed, grounded and safe. So the eval did not wait for the ML
model — and it found three things worth fixing.

| Finding | Before | After |
|---|---|---|
| SMS losing part of the instruction | **51%** (828/1,625) | **0%** |
| Advisories with no in-season action | **39.8%** (647) | **0%** |
| `cold_stress` never exercised by the golden set | not covered | covered |

**SMS truncation.** Half of all 2G messages had the instruction cut mid-sentence
— on that channel the SMS *is* the advisory. Fixed with an authored `sms_action`
short form per rule, rather than truncating the long form. Max SMS is now 143
characters.

**No-action advisories.** 4 farmers in 10 triggered no driver rule and received
only post-harvest boilerplate. A healthy field now gets an explicit all-clear.
We deliberately did **not** loosen thresholds to manufacture advice: false alarms
erode trust faster than silence does.

Also confirmed by the same run: no dead rules (all 8 fire between 4.0% and
22.7%), conflict resolution fires on 5.3% of rows, and data-quality suppression
catches the ~6% of rows with implausible NDVI/GNDVI/SAVI.

### Integration gap: prediction intervals

Confidence classification scored 100% "high" — an artefact of the synthetic
intervals used in the harness. `src/service.py` returns a bare point prediction
with **no interval**, so the hedging path has never seen real input.

Without an interval, the advisory can never tell a farmer when to distrust it.
That is a guarantee already built and currently unreachable. Quantile regression
or bootstrapped residuals on the ML side would close it.

### The golden set

`tests/fixtures/golden/golden_set.json` — 32 forecasts, stratified rather than
random. `critical` is 1.0% of real rows, so uniform sampling would have put
roughly zero of our worst-news cases in the set, and that is precisely the copy
most in need of review. Each band gets equal weight; data-quality, low-confidence,
no-area, unknown-crop, both absolute-threshold rules and the water conflict are
represented explicitly.

`scripts/advisory_eval.py` scores it and `tests/test_advisory_golden_set.py`
runs the same gates in CI, so a regression fails a build instead of surfacing in
a demo.

```bash
python scripts/advisory_eval.py                              # offline, all gates
python scripts/advisory_eval.py --review-sheet review.md     # native-speaker packet
python scripts/advisory_eval.py --live                       # real providers, ~$0.25/1000
```

Current result: **32/32 on every gate** — schema validity, numeric fidelity,
safety, band consistency, SMS length, SMS instruction intact — both offline and
against the live provider.

### Live run (Azure AI Foundry, `gpt-5.2`)

| | |
|---|---|
| Gates passed | 32/32 |
| Generation path | 100% `llm` — no fallbacks, no provider errors |
| Latency | p50 5.1 s, p95 6.0 s, max 9.0 s |
| Cost | ~$0.25 per 1,000 advisories; SMS path free |

Two prompt defects the live run exposed, both now fixed in `system.md`:

1. **The body restated every action**, which the `What to do:` list then repeated
   verbatim — the advisory was half duplicate text.
2. **Band labels leaked mid-sentence** with their capital ("expected to be Above
   typical"), and `baseline_ratio` appeared as a bare decimal ("0.64 of
   typical") where a farmer reads percentages.

A third defect surfaced on a later live run, and it was **ours, not the
model's**: `baseline_ratio` of 0.901 was correctly written as "90.1%", but the
numeric check only tolerated the rounded integer "90" and threw the advisory
away. A correct advisory was being discarded 3% of the time. Fixed by accepting
every faithful rendering of a ratio, with a test that the check still rejects a
nearby invention.

None of the three was catchable offline: `FakeProvider` returns what the test
author wrote, so only a real model produces real wording — and only real wording
exposes a validator that is too strict. This is the argument for keeping a live
run in the loop even though every automated gate was already green.

**Latency note:** 5 seconds p50 is fine for a push advisory generated at
forecast time and cached, and it is slow for a synchronous HTTP request. Since
the advisory fires once per season and is cached, the endpoint mostly serves
cache hits. If that changes, generate asynchronously via the trigger.

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

Order is Azure → Gemini → OpenAI, each skipped without a network call if its key
is absent. **All are optional**: with none set the service still runs and serves
rules-only text.

```bash
# .env (gitignored)
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://<resource>.services.ai.azure.com/openai/v1
AZURE_OPENAI_DEPLOYMENT=gpt-5.2
```

The endpoint is the `/openai/v1` **base** — the provider appends
`/chat/completions` itself. Endpoint and deployment come from the environment so
no tenant-specific value is committed.

Azure AI Foundry's `/openai/v1` route is OpenAI-compatible down to Bearer auth,
so it reuses `OpenAIProvider`. Two things genuinely vary between deployments and
are therefore config rather than constants:

- `token_param` — this deployment **rejects `max_tokens` outright** and requires
  `max_completion_tokens`. Verified against the live endpoint.
- `send_temperature` — some reasoning models reject a non-default temperature.
  `gpt-5.2` accepts it, so it stays on.

Model choice and timeouts live in
[`configs/advisory_llm.yaml`](../configs/advisory_llm.yaml), kept separate from
the rules config so swapping a model does not invalidate the cache.

The test suite unsets every provider key before hitting the API endpoints, so a
developer with a live key exported cannot be billed by running `pytest`.

Bump `rules_version` in `configs/advisory_rules.yaml` on **any** threshold
change — it is part of the cache key and is stamped on every advisory.

## Status against the work plan

- **D1–D2 Scope prompts & advisory rules** — done: rules table, both contracts,
  prompt templates, 10 fixtures.
- **D3–D4 Build & trigger LLM** — done: Gemini + OpenAI adapters, validation with
  repair retry, rules fallback, cache, `POST /api/v1/advisory`, `/sms`,
  `/health`, on-prediction-complete trigger with sinks. 143 tests passing.
- **D5–D6 Test on real predictions** — done, except for two things needing other
  people. 1,625-row coverage run, 32-item stratified golden set, eval harness,
  CI gates, live provider verified at 32/32, translation wired and verified.
  Four defects found and fixed along the way: SMS truncation (51%), no-action
  advisories (40%), duplicated action text, and an over-strict numeric check.
  **Outstanding:** native-speaker sign-off on the three languages (sheets are
  ready), and re-running against the ML track's real forecasts once they exist —
  the harness takes them unchanged.
- **D7–D8 QA & polish** — red-team prompts, season performance report,
  observability, demo script with pre-cached farms.

## Translation

**Generate in English, then translate.** Not generate-directly-in-language —
`check_safety` matches English terms and is blind to a banned topic introduced in
Kinyarwanda. English is the only language we can actually police, so the English
passes every gate first and translation is confined to rephrasing approved copy.

A translation is then verified in its own right: numbers preserved (digits are
language-independent), action count unchanged, and not silently returned
untranslated. **If verification fails, the farmer gets the verified English** —
correct English beats a translation we cannot check.

Non-English costs 2 calls and ~11 s, against 1 call and ~5 s for English. Both
are cached, and the advisory fires once per season.

### SMS strings are translated at build time, not per message

There are only ~15 short strings per language. Translating them once
(`scripts/build_sms_translations.py` → `configs/advisory_i18n.yaml`) means:

- a native speaker reviews **one small file** in a few minutes, not hundreds of
  near-identical messages
- the 2G path stays deterministic and **free**
- a reviewed language is never overwritten by re-running the script

Fallback is per string, so a partially translated language still sends a usable
message. Verified across all 1,625 rows: `en` max 143 chars, `sw` 144, `rw` 122,
`fr` 143 — no truncation in any language.

`review_status` on each language is **not a gate**. It exists so the report can
state honestly which languages a human has actually checked. All three are
currently `unreviewed`.

Review sheets:

```bash
python scripts/advisory_eval.py --translation-sheet docs/advisory_translation_review.md
python scripts/advisory_eval.py --review-sheet docs/advisory_review_sheet.md
```

### Not yet built, deliberately

- **No language has been reviewed by a native speaker.** The strings are machine
  translation, and the review sheet is ready. Until someone signs off, non-English
  output is plausible but unverified by a human.
- **Cache is in-process.** Fine for the demo, wrong for multiple workers.
- **Gemini is configured but unused** — no `GEMINI_API_KEY` yet. It sits second
  in the chain and will be picked up automatically when a key appears; nothing
  else needs changing.
