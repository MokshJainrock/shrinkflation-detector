# Shrinkflation Detector

Tracks shrinkflation in grocery products. Shrinkflation is when a product gets smaller but the price stays the same (or goes up), so you quietly pay more per ounce.

The project has two layers of data:

1. A fixed list of 610+ shrinkflation cases that were documented by public research (BLS size tracking, Consumer Reports, mouseprint.org, FTC complaints, news coverage). Every case keeps a reference to where it was reported.
2. A live pipeline that pulls real product sizes from Open Food Facts and real shelf prices from the Kroger API, and saves timestamped snapshots every 30 minutes. This part grows on its own: when the same product shows up later with a smaller size and a higher price per unit, a new case gets flagged, so the total case count keeps climbing past the documented baseline.

Everything ends up in a Streamlit dashboard. There is also a small GPT-4o agent that can query the database and write daily/weekly summaries.

## Live demo

[shrinkflation-detector-t2ltg2v33krb7w2fsdup4a.streamlit.app](https://shrinkflation-detector-t2ltg2v33krb7w2fsdup4a.streamlit.app/)

## Data sources

| Source | What it provides |
|--------|-----------------|
| Documented research | 610+ verified cases (BLS, Consumer Reports, mouseprint.org, FTC, major news outlets, r/shrinkflation) |
| [Open Food Facts API](https://world.openfoodfacts.org/) | Product sizes, barcodes, brands. Crowdsourced, free, no API key |
| [Kroger API](https://developer.kroger.com/) | Real US retail shelf prices (free developer account needed) |

Nothing is fabricated or simulated. Historical and live records are labeled separately in the database (`documented_historical` vs `live_*`) and the detector never mixes them.

## How detection works

The detector is deliberately strict. A live flag only gets created when:

- the same product was observed twice, at least 30 days apart, with a confirmed size and price each time
- both observations use the same unit family (mass, volume, or count)
- the size dropped by at least 2%
- the price per unit went up

That last point matters: a bag that goes from 9.75 oz at $4.99 to 9.25 oz at $4.89 looks like a price cut, but per ounce it went from $0.512 to $0.528. That's shrinkflation, and the detector catches it.

If the evidence is ambiguous in any way (multiple size readings in the pairing window, unknown units, etc.) the case is rejected. I'd rather miss a real case than report a fake one. Every flag stores links to the exact snapshots used as evidence, so you can audit any result.

Severity is based on the price-per-unit increase: HIGH is 20%+, MEDIUM is 8%+, anything below is LOW.

## Setup

```bash
git clone https://github.com/MokshJainrock/shrinkflation-detector.git
cd shrinkflation-detector
pip install -r requirements.txt
cp .env.example .env
python main.py --init
```

Keys go in `.env` (or Streamlit secrets if you deploy there):

- `KROGER_CLIENT_ID` / `KROGER_CLIENT_SECRET` for live prices
- `OPENAI_API_KEY` if you want the AI insights
- `DATABASE_URL` is optional, defaults to a local SQLite file

## Usage

```bash
python main.py --init         # create DB tables
python main.py --scrape       # one ingestion tick (Open Food Facts + Kroger)
python main.py --analyze      # run the detector
python main.py --insight      # daily AI insight
python main.py --report       # weekly AI report
python main.py --all          # scrape + analyze + insight
python main.py --schedule     # run --all every 24 hours
python main.py --live         # keep ingesting every 30 minutes until Ctrl+C
python main.py --seed         # one full ingestion cycle via the pipeline
python main.py --dashboard    # Streamlit on localhost:8501
```

On a server you'd run `--live` for continuous collection. The hosted demo on Streamlit Cloud can't run background jobs, so there the scan runs on a 30 minute cache window whenever the page is loaded (a scheduled GitHub Action visits the app to keep this going).

## Dashboard

Seven tabs: Overview, Live Tracking, Compare, Deep Dive, Explorer, AI Insights, and Methodology. The Methodology tab explains the detection rules and where every piece of data comes from.

## Project layout

```
main.py              CLI entrypoint
config/              settings, thresholds, API endpoints
db/                  SQLAlchemy models
data/                verified historical cases + loader
scraper/             Open Food Facts tracker, Kroger price scraper
ingestion/           pipeline + 30-minute scheduler
analysis/            the detector
agent/               GPT-4o analyst with function-calling tools
dashboard/           Streamlit app
tests/               detector tests
```

## Stack

Python, Streamlit, SQLAlchemy (SQLite/Postgres), APScheduler, Plotly, Pandas, OpenAI API, Requests
