# YieldSense

Crop yield forecasting and AI advisory for African smallholder farmers.

Carnegie Mellon University Africa — *Applications of AI in Africa*.
Akhabue Daniel Osaro · Afolabi Paul Okikijesu · Kitonge Levis ·
Martin Muchuki Irungu · Emmanuel Musundi Nyanja

## The problem

Most smallholder farmers in Africa have no reliable way to anticipate how a
season will perform. Without a yield estimate, decisions about planting
schedules, resource allocation and market timing are guesswork.

YieldSense predicts seasonal yield from climate, satellite and historical data,
then turns that prediction into advice a farmer can act on — with particular
attention to **post-harvest decisions**: storage, drying, labour, and when to
sell.

## Architecture

Four layers, per the project proposal:

| Layer | What it does |
|---|---|
| **User** | Web app, and SMS over 2G for farmers without smartphones |
| **Platform** | Mobile-first responsive web app |
| **Intelligence** | ML yield prediction · GenAI advisory · chatbot |
| **Data** | Climate, geographical and historical yield data |

## Tracks and status

| Track | Owner | Status |
|---|---|---|
| Data & ML | — | In progress |
| **GenAI Advisory** | Martin | **Built** — see [docs/ADVISORY.md](docs/ADVISORY.md) |
| Chatbot | — | In progress |
| Platform / Backend | — | In progress |

### GenAI Advisory

Turns a yield forecast into a written recommendation, once per season, in four
languages, delivered to web and to a single 160-character SMS.

The design rule is that **the rules engine decides and the LLM only narrates**.
Every band, threshold and quantity a farmer sees is computed deterministically;
the model rephrases and translates what the rules already decided, and every
generated response is validated before it can reach anyone. This is what makes
the advisory safe to ship, testable without an API key, and functional when the
provider is down.

Full design, guarantees, evaluation results and known limitations:
**[docs/ADVISORY.md](docs/ADVISORY.md)**.

```python
from src.advisory import on_prediction_complete, register_sink

register_sink(save_to_db)
register_sink(queue_sms)
advisory = on_prediction_complete(prediction)   # once per season
```

```python
from src.advisory.api import router as advisory_router
app.include_router(advisory_router)   # POST /api/v1/advisory, /sms, GET /health
```

## Setup

Requires Python 3.9+.

```bash
git clone https://github.com/Apprentice-doa/YieldSense-Crop-Yield-Forecasting-Carnegie-Mellon-University.git
cd YieldSense-Crop-Yield-Forecasting-Carnegie-Mellon-University

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # then fill in any provider keys you have
```

**API keys are optional.** With none set, the advisory service still runs and
serves its deterministic rules-only text. See
[docs/ADVISORY.md](docs/ADVISORY.md#configuring-providers) for provider setup.

### Verify

```bash
pytest tests/ --no-cov     # runs fully offline; no API key used or needed
black --check src/ tests/
flake8 src/ tests/
```

### Useful scripts

| Command | Purpose |
|---|---|
| `python scripts/advisory_eval.py` | Score the advisory against the golden set |
| `python scripts/advisory_eval.py --live` | Same, against a real provider |
| `python scripts/advisory_coverage_report.py` | Rule behaviour across the whole dataset |
| `python scripts/advisory_demo.py` | Warm the cache and print demo advisories |
| `python scripts/season_report.py` | Predicted vs actual season performance |

## Data

`data/raw/crop_prediction_gee_computations.csv` — 1,625 rows, 90 fields, 30
crops, Jan–May 2023, carrying both the original feature columns and real Google
Earth Engine computations (`gee_ndvi`, `gee_rainfall`, `gee_temp`, …).

**Known limitations, stated plainly** because they constrain what the system may
honestly claim:

- **`yield` appears to be synthetic.** The original feature columns predict it
  almost perfectly (rainfall alone, r = 0.756) while the real GEE measurements
  barely do (r = 0.162). The most economical explanation is that `yield` was
  generated *from* those columns. **A model trained on them will report
  excellent accuracy and have learned nothing about agriculture.**
- **Single season only.** No multi-year history, so "typical" is a
  within-dataset crop mean, not a district historical average.
- **Not African data.** The earlier export placed the fields at ~22.6°N, 88.5°E
  (West Bengal, India); the GEE export drops latitude and longitude.
- **`yield` has no units**, and there is no field area, so post-harvest
  quantities are structurally correct but not yet interpretable.
- **Real data has gaps.** `gee_temp` is missing for 95 rows and `gee_rainfall`
  for 26. Handled, not imputed.

These are documented rather than worked around. Advisory copy is written to
match what the data actually supports.

## Documentation

- **[GenAI Advisory](docs/ADVISORY.md)** — design, guarantees, evaluation
- [Onboarding](docs/ONBOARDING.md) · [Development](docs/DEVELOPMENT_GUIDE.md) ·
  [Coding standards](docs/CODING_STANDARDS.md)
- [Git workflow](docs/GIT_WORKFLOW.md) · [Contributing](CONTRIBUTING.md)
- [Data management](docs/DATA_MANAGEMENT.md) · [ML workflow](docs/ML_WORKFLOW.md)

## Project structure

```
├── configs/               # Rules, baselines, LLM and i18n configuration
├── data/                  # Datasets (gitignored except .gitkeep)
├── docs/                  # Documentation and review sheets
├── notebooks/             # Exploration
├── scripts/               # Reproducible build, evaluation and demo scripts
├── src/
│   └── advisory/          # GenAI Advisory track
├── tests/                 # Unit, integration and golden-set tests
└── .github/               # Workflows and templates
```
