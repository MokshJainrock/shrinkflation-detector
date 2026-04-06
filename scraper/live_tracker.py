"""Live-only tracker for Open Food Facts ingestion."""

from config.settings import OFF_CATEGORIES
from db.models import init_db
from scraper.openfoodfacts import ingest_categories, select_rotating_categories


def run_live_update(max_categories=5):
    """
    Fetch a rotating set of categories from Open Food Facts and ingest them.

    This stores only live API-backed product rows and size snapshots.
    Shrinkflation flags are calculated later by the detector from those snapshots.
    """
    init_db()
    categories = select_rotating_categories(OFF_CATEGORIES, max_categories)
    return ingest_categories(categories)


if __name__ == "__main__":
    print("Running live tracker update...")
    result = run_live_update()
    print(f"Done: {result}")
