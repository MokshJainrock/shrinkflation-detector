# Shrinkflation Detector

A live-only pipeline that scans Open Food Facts every 60 seconds, stores only source-backed product observations, and flags shrinkflation only after a product is seen to shrink across multiple live scans.

There is no bundled historical dataset, no seeded shrinkflation cases, and no fabricated rows in the application database.

## How It Works

```
Open Food Facts API ──→ SQLite DB ──→ Detector ──→ Dashboard
(every 60 seconds)      (live rows)    (size-only   (auto-refresh
                                        or size+    every 60s)
                                        price)
```

1. Every 60 seconds the scanner fetches a rotating set of categories from the Open Food Facts v2 search API.
2. Products are keyed by barcode when available, normalized, and stored only if the API returns a valid name plus a parseable package size.
3. A new size snapshot is written only when the live package size actually changes.
4. The detector compares the two newest live size snapshots for each product and flags real observed shrink events.
5. If Kroger credentials are configured, exact UPC matches can add live price snapshots for price-per-unit calculations.

## Data Sources

| Source | What it provides | How it is used |
|--------|-------------------|----------------|
| [Open Food Facts API](https://world.openfoodfacts.org/) | Product names, brands, barcodes, package sizes | Primary live product source |
| [Kroger API](https://developer.kroger.com/) | Store-specific prices | Optional price enrichment, exact UPC matches only |

## Accuracy Guardrails

- No static shrinkflation seed data is loaded into the database.
- Open Food Facts rows are ignored unless the API returns a valid product name and parseable size.
- Package sizes are normalized before comparison so `kg`, `g`, `oz`, `L`, `ml`, and `fl oz` do not drift into mismatched stats.
- Kroger prices are attached only through exact UPC lookups, not fuzzy name matching.
- Shrinkflation flags are created from observed live size changes, not guessed from static case lists.

Open Food Facts is a real but crowd-sourced database, so the app can enforce provenance and consistency checks, but it cannot guarantee more truth than the upstream source provides.

## CLI

```bash
python main.py --live       # Start the live scanner (every 60s)
python main.py --seed       # Run one live ingestion tick
python main.py --reseed     # Wipe DB then run one live ingestion tick
python main.py --dashboard  # Launch Streamlit dashboard
```

## Tech Stack

Python, Streamlit, SQLAlchemy, SQLite, APScheduler, Plotly, Requests
