"""Run all seed scripts to populate the database with POI data.

Usage:
    python backend/scripts/seed_all.py
"""

import sys
import time
from pathlib import Path

# Ensure the `backend` package is importable when run as a script
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.seed_base import get_sync_engine  # noqa: E402
from scripts.seed_chengdu import seed_chengdu  # noqa: E402
from scripts.seed_hangzhou import seed_hangzhou  # noqa: E402


def main() -> None:
    """Seed all cities into the database."""
    print("=" * 50)
    print("  AI Travel Planner — Database Seed Script")
    print("=" * 50)

    start = time.monotonic()

    # Verify database connectivity before seeding
    engine = get_sync_engine()
    try:
        with engine.connect() as conn:
            conn.execute(conn.execution_options(isolation_level="autocommit"))
            # Simple query to confirm PostGIS is available
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
        print("Database connection: OK\n")
    except Exception as exc:
        print(f"ERROR: Cannot connect to database — {exc}")
        sys.exit(1)

    print("Seeding cities...\n")

    seed_hangzhou()
    seed_chengdu()

    elapsed = time.monotonic() - start
    print(f"\nDone in {elapsed:.1f}s")
    print("=" * 50)


if __name__ == "__main__":
    main()
