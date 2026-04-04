# Shrinkflation Detector

A **live** data pipeline that scans Open Food Facts every 60 seconds, detects shrinkflation (when products get smaller but prices stay the same or increase), and shows results in a real-time dashboard.

**No seed data. No historical records. Every product comes from a live API call.**

## Live Demo

[shrinkflation-detector-t2ltg2v33krb7w2fsdup4a.streamlit.app](https://shrinkflation-detector-t2ltg2v33krb7w2fsdup4a.streamlit.app/)

## How It Works

```
Open Food Facts API ──→ APScheduler ──→ SQLite DB ──→ Detector ──→ Dashboard
(every 60 seconds)      (background)    (snapshots)   (compare     (auto-refresh
                                                       sizes)       every 60s)
```

1. **Every 60 seconds**: Scanner fetches real products from [Open Food Facts](https://world.openfoodfacts.org/) — 2 categories per tick, rotating through 17 categories (chips, cereal, ice cream, yogurt, cookies, crackers, pasta, candy, bread, coffee, ketchup, mayo, peanut butter, juice, frozen meals, detergent, soap)
2. **Snapshot stored**: Each product's current size, brand, barcode saved with timestamp
3. **Detection**: If same product appears later with a smaller size → shrinkflation flag created
4. **Dashboard**: Auto-refreshes every 60 seconds to show latest scan results

## Data Sources

| Source | What it provides |
|--------|-----------------|
| **[Open Food Facts API](https://world.openfoodfacts.org/)** | Real product sizes, barcodes, brands — crowdsourced, free, no API key |
| **[Open Prices API](https://prices.openfoodfacts.org/)** | Crowd-sourced real retail prices from scanned grocery receipts |

Zero fabricated, random, simulated, or seeded data.

## Features

- **Live scanner** — fetches real products every 60 seconds via APScheduler
- **Shrinkflation detector** — flags products whose size decreased >2%
- **Severity scoring** — HIGH (>10%), MEDIUM (5-10%), LOW (<5%)
- **Real-time dashboard** — auto-refreshes every 60 seconds
- **Filters** — by category, brand, severity, retailer, time range
- **Charts** — worst brands, severity breakdown, category analysis, trends

## CLI

```bash
python main.py --live       # Start live scanner (every 60s, runs until Ctrl+C)
python main.py --seed       # Run one scan tick
python main.py --reseed     # Wipe DB then run one scan tick
python main.py --dashboard  # Launch Streamlit dashboard
```

## Tech Stack

Python, Streamlit, SQLAlchemy (SQLite), APScheduler, Plotly, Requests
