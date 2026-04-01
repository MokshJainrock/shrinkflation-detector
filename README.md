# Shrinkflation Detector

A production-ready web app that tracks grocery product sizes and prices over time, detects shrinkflation (when products get smaller but prices stay the same or increase), and surfaces findings through an AI-powered dashboard.

## Why This Matters

- **Consumers**: See which brands are secretly raising prices by shrinking products
- **Journalists**: Data-driven stories on corporate pricing deception
- **Policy**: Evidence for consumer protection and price transparency legislation

## Architecture

```
Open Food Facts API  ─┐
                       ├──→  PostgreSQL  ──→  Detector  ──→  Streamlit Dashboard
Kroger API (prices)  ──┘     (products,       (flags         (charts, tables,
                              snapshots)       shrinks)       AI insights)
                                                  ↑
                                           Claude AI Agent
                                        (analysis, Q&A, reports)
```

## Features

- **Daily scraping** from Open Food Facts (free) + Kroger (free developer account)
- **Shrinkflation detector** compares product sizes over 30 days, flags decreases > 2%
- **Severity scoring**: HIGH (>5% hidden increase), MEDIUM (2-5%), LOW (<2%)
- **AI Agent** powered by Claude that can:
  - Answer natural language questions about the data
  - Generate daily insights automatically
  - Compile weekly markdown reports with executive summaries
  - Stream responses token-by-token in the dashboard
- **Live dashboard** with auto-refresh, interactive charts, and search/filter
- **50 pre-loaded products** with 90 days of data via `--seed`

## Quick Start (5 minutes)

### 1. Prerequisites

- Python 3.11+
- PostgreSQL running locally

### 2. Install

```bash
cd shrinkflation-detector
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env` with your credentials:
- `DATABASE_URL` — your PostgreSQL connection string
- `ANTHROPIC_API_KEY` — for AI features (get at console.anthropic.com)
- `KROGER_CLIENT_ID` / `KROGER_CLIENT_SECRET` — optional, for price data

### 4. Run with sample data

```bash
createdb shrinkflation_db
python main.py --seed        # Loads 50 products, 90 days of data, 25 flags
python main.py --dashboard   # Opens at http://localhost:8501
```

## Getting API Credentials

### Kroger (free)

1. Go to [developer.kroger.com](https://developer.kroger.com)
2. Create an account and register a new app
3. Copy your Client ID and Client Secret into `.env`

### Anthropic (for AI features)

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an API key
3. Add to `.env` as `ANTHROPIC_API_KEY`

## CLI Commands

```bash
python main.py --init         # Create database tables
python main.py --seed         # Load demo data (safe to run multiple times)
python main.py --scrape       # Scrape Open Food Facts + Kroger
python main.py --analyze      # Run shrinkflation detector
python main.py --insight      # Generate AI daily insight
python main.py --report       # Generate AI weekly report
python main.py --all          # Scrape + analyze + insight
python main.py --schedule     # Auto-run every 24 hours
python main.py --dashboard    # Launch Streamlit dashboard
```

## Dashboard Features

1. **Metrics row** — total products, monthly shrinks, avg hidden increase, worst category
2. **Worst brands chart** — horizontal bar chart of top offenders
3. **Weekly trend** — line chart of new shrinkflation detections over time
4. **Category breakdown** — shrinkflation rate by product category
5. **AI Insights** — auto-generated daily insight + "Ask the Data" chatbot
6. **Flagged products table** — searchable, filterable, color-coded by severity
7. **Product deep dive** — full history timeline for any product

## Example AI Insights

> "Cereal brands reduced package sizes 3x more than any other category this week, with Kellogg's leading at 3 new shrinkflation flags. Frosted Flakes dropped from 19.2 oz to 16.9 oz while the price increased by $0.20 — a hidden +15.8% price increase per ounce."

> "Frito-Lay has the most shrinkflation flags of any brand (5 this month), but Nestlé's Häagen-Dazs has the highest average real price increase at +12.3% per ounce. Ice cream is now the fastest-growing shrinkflation category."

## Project Structure

```
shrinkflation-detector/
├── main.py                  # CLI entrypoint + seed data generator
├── config/
│   └── settings.py          # API keys, DB config, thresholds
├── scraper/
│   ├── openfoodfacts.py     # Open Food Facts API scraper
│   └── kroger.py            # Kroger API scraper with OAuth2
├── db/
│   └── models.py            # SQLAlchemy models (4 tables)
├── analysis/
│   └── detector.py          # Shrinkflation detection logic
├── agent/
│   ├── tools.py             # 8 agent tool definitions
│   └── analyst.py           # Claude AI agent with agentic loop
├── dashboard/
│   └── app.py               # Streamlit dashboard
├── requirements.txt
├── .env.example
└── README.md
```

## Live Demo

[your-app.streamlit.app](https://your-app.streamlit.app)
