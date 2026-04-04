# Shrinkflation Detector

A data pipeline and dashboard that tracks grocery product sizes and prices, detects shrinkflation (when products get smaller but prices stay the same or increase), and surfaces findings through an interactive dashboard.

## Live Demo

[shrinkflation-detector-t2ltg2v33krb7w2fsdup4a.streamlit.app](https://shrinkflation-detector-t2ltg2v33krb7w2fsdup4a.streamlit.app/)

## Why This Matters

- **Consumers**: See which brands are secretly raising prices by shrinking products
- **Journalists**: Data-driven stories on corporate pricing deception
- **Policy**: Evidence for consumer protection and price transparency legislation

## Data Sources

| Source | What it provides | Type |
|--------|-----------------|------|
| **BLS, Consumer Reports, FTC, mouseprint.org, media** | 543 verified shrinkflation cases with documented old/new sizes and prices | Baseline (loaded on first deploy) |
| **Open Food Facts API** | Real product sizes, barcodes, brands — crowdsourced, free, no API key | Scheduled pipeline (hourly when app is active) |
| **Open Prices API** | Crowd-sourced real retail prices from scanned grocery receipts | Scheduled pipeline (daily) |

No fabricated, random, or simulated data. Every record traces to a documented public source or a live API response.

## Architecture

```
Verified Cases (BLS/CR/FTC)  ──→  SQLite DB  ──→  Detector  ──→  Streamlit Dashboard
                                      ↑               ↓            (charts, filters,
Open Food Facts API ─────────────→  Snapshots     Flags              AI insights)
Open Prices API ─────────────────→  (scheduled)   (severity)
                                      ↑
                              APScheduler (background)
                              • Hourly: OFF category scan
                              • Daily: verified case deep-scan
```

## How the Pipeline Works

1. **On first deploy**: 543 verified cases × 9 retailers = 5,598 products loaded instantly (<1 second)
2. **Every hour** (when app is active): APScheduler fetches the most recently updated products from Open Food Facts, stores new size snapshots, runs the shrinkflation detector
3. **Daily at 03:00 UTC**: Deep-scans all verified cases via OFF API to get current live sizes, cross-references with Open Prices API for real retail prices, discovers new size changes
4. **Detection**: Compares current snapshot vs previous — flags any product whose size decreased >2%

## Features

- **Shrinkflation detector** compares product sizes over time, flags decreases > 2%
- **Severity scoring**: HIGH (>10% hidden increase), MEDIUM (5-10%), LOW (<5%)
- **Scheduled data pipeline** via APScheduler — hourly OFF scan + daily deep-scan
- **AI Agent** powered by OpenAI that can:
  - Answer natural language questions about the data
  - Generate daily insights automatically
  - Compile weekly markdown reports
- **Interactive dashboard** with auto-refresh, Plotly charts, and search/filter
- **5,598 real products** from documented shrinkflation investigations

## Dashboard Tabs

1. **Metrics row** — total products, shrinks detected, avg hidden increase, worst category/brand
2. **Worst brands chart** — horizontal bar chart of top offenders
3. **Weekly trend** — line chart of new shrinkflation detections over time
4. **Category breakdown** — shrinkflation rate by product category
5. **AI Insights** — auto-generated daily insight + "Ask the Data" chatbot
6. **Flagged products table** — searchable, filterable, color-coded by severity
7. **Product deep dive** — full history timeline for any product

## CLI Usage

```bash
python main.py --seed       # Run one full ingestion cycle (live APIs)
python main.py --reseed     # Wipe DB then run fresh live ingestion
python main.py --live       # Start continuous scheduler (hourly + daily)
python main.py --analyze    # Run shrinkflation detector on all products
python main.py --dashboard  # Launch Streamlit on localhost:8501
```

## Honest Status

| Claim | Status |
|-------|--------|
| Real verified data | ✅ 543 documented cases from BLS, Consumer Reports, FTC, media |
| Live API integration | ✅ Open Food Facts + Open Prices APIs, scheduled via APScheduler |
| Continuously running 24/7 | ⚠️ Runs while Streamlit Cloud app is active (sleeps when idle) |
| Real retail prices | ✅ Crowd-sourced from Open Prices (receipt scans), not fabricated |

## Tech Stack

Python, Streamlit, SQLAlchemy (SQLite), APScheduler, Plotly, Requests
