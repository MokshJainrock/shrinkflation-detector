# Shrinkflation Detector

A hybrid shrinkflation analytics system that combines **610+ documented, verified shrinkflation cases** from public research with a **live data pipeline** that tracks real product sizes and prices over time — all surfaced in an interactive Streamlit dashboard with an AI analyst on top.

Shrinkflation = a product gets smaller while its price stays the same (or rises), so the **price per unit** quietly goes up.

## Live Demo

[shrinkflation-detector-t2ltg2v33krb7w2fsdup4a.streamlit.app](https://shrinkflation-detector-t2ltg2v33krb7w2fsdup4a.streamlit.app/)

## How It Works

```
                ┌─ Documented cases (610+ verified, with sources) ─┐
                │                                                   │
Open Food Facts ┤                                                   ├─→ SQLite DB ─→ Detector ─→ Dashboard + AI Analyst
(sizes/barcodes)│                                                   │   (snapshots)   (strict,     (Streamlit)  (GPT-4o)
                └─ Kroger API (real US retail shelf prices) ────────┘                  evidence-
                                                                                       based)
```

1. **Historical layer** — 610+ verified shrinkflation cases seeded from published research (BLS size tracking, Consumer Reports, mouseprint.org, FTC complaints, major media reports). Every case carries its source.
2. **Live layer** — an ingestion pipeline fetches real product sizes from Open Food Facts and real shelf prices from the Kroger API, storing timestamped snapshots. Runs every 30 minutes: as a true APScheduler background job via `python main.py --live` (local/server), or on a 30-minute cache window per page load on Streamlit Cloud.
3. **Detection** — a strict, evidence-based detector compares enriched observations over time and flags products whose size shrank while price-per-unit rose.
4. **Dashboard** — Streamlit app with 7 tabs: Overview, Live Tracking, Compare, Deep Dive, Explorer, AI Insights, Methodology.
5. **AI analyst** — a GPT-4o agent with function-calling tools queries the database directly to generate daily insights and weekly reports.

## Data Sources

| Source | What it provides |
|--------|-----------------|
| **Documented research** | 610+ verified cases from BLS, Consumer Reports, mouseprint.org, FTC, NYT/WSJ/CNN/NPR/BBC, r/shrinkflation |
| **[Open Food Facts API](https://world.openfoodfacts.org/)** | Real product sizes, barcodes, brands — crowdsourced, free, no API key |
| **[Kroger API](https://developer.kroger.com/)** | Real US retail shelf prices (requires free API credentials) |

Historical and live data are strictly separated in the database (`documented_historical` vs `live_*` source labels) — documented cases are never mixed into live detection.

## Detection Methodology

A live flag is created **only** when all of the following hold:

- Two enriched observations (confirmed size **and** price) exist for the same product, at least **30 days apart**
- Price-only snapshots may be paired with a size snapshot within a **24-hour window** — but only if the pairing is unambiguous
- Both observations use the same unit family (mass / volume / count)
- Size decreased by at least **2%**
- **Price per unit** strictly increased — e.g. 9.75 oz at $4.99 → 9.25 oz at $4.89 is still shrinkflation ($0.512/oz → $0.528/oz, +3.1%) even though the shelf price fell
- Every flag links to its evidence snapshots (old/new price and size snapshots)

Ambiguous evidence is conservatively rejected: **false negatives are preferred over false positives.**

Severity is scored by price-per-unit increase: **HIGH** (≥20%), **MEDIUM** (≥8%), **LOW** (below).

## Setup

```bash
git clone https://github.com/MokshJainrock/shrinkflation-detector.git
cd shrinkflation-detector
pip install -r requirements.txt
cp .env.example .env   # then fill in your keys
python main.py --init
```

### Environment variables (`.env`)

| Variable | Required for | Notes |
|----------|--------------|-------|
| `DATABASE_URL` | optional | Defaults to `sqlite:///shrinkflation.db` |
| `KROGER_CLIENT_ID` / `KROGER_CLIENT_SECRET` | live price ingestion | Free at [developer.kroger.com](https://developer.kroger.com/) |
| `OPENAI_API_KEY` | AI insights/reports | GPT-4o with function calling |

On Streamlit Cloud, the same keys can be set via Streamlit secrets instead.

## CLI

```bash
python main.py --init         # Create all DB tables
python main.py --scrape       # Run one ingestion tick (Open Food Facts + Kroger)
python main.py --analyze      # Run the strict evidence-based detector
python main.py --insight      # Generate and print daily AI insight
python main.py --report       # Generate and print weekly AI report
python main.py --all          # Scrape + analyze + insight
python main.py --schedule     # Run --all every 24 hours automatically
python main.py --live         # Continuous ingestion every 30 minutes (Ctrl+C to stop)
python main.py --seed         # Run one full ingestion cycle via the pipeline
python main.py --dashboard    # Launch Streamlit dashboard on localhost:8501
```

## Dashboard

- **Overview** — headline stats, worst offending brands, severity and category breakdowns
- **Live Tracking** — tracking funnel and freshly detected flags from the live pipeline
- **Compare** — side-by-side before/after product comparison
- **Deep Dive** — per-brand analysis and product snapshot timelines
- **Explorer** — filterable raw data browser
- **AI Insights** — GPT-4o-generated daily insights and weekly reports
- **Methodology** — full explanation of detection rules and data provenance

## Project Structure

```
├── main.py              # CLI entrypoint
├── config/              # Settings, thresholds, API endpoints, secrets loading
├── db/                  # SQLAlchemy models (products, snapshots, flags, insights)
├── data/                # 610+ verified historical cases + loader
├── scraper/             # Open Food Facts live tracker + Kroger price scraper
├── ingestion/           # Pipeline orchestration + APScheduler scheduler
├── analysis/            # Strict evidence-based shrinkflation detector
├── agent/               # GPT-4o analyst with function-calling DB tools
├── dashboard/           # Streamlit app (7 tabs)
└── tests/               # Detector unit tests
```

## Tech Stack

Python · Streamlit · SQLAlchemy (SQLite) · APScheduler · Plotly · Pandas · OpenAI (GPT-4o) · Requests
