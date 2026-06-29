"""Shared utilities for seed scripts."""

import sys
from pathlib import Path
from typing import Any

from geoalchemy2 import WKTElement
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

# Add backend root to sys.path so `app` package is importable
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings  # noqa: E402
from app.models.poi import Base, POI  # noqa: E402


def get_sync_engine():  # noqa: ANN201
    """Create a synchronous SQLAlchemy engine from the async database URL."""
    url = settings.database_url.replace("+asyncpg", "+psycopg2")
    return create_engine(url, echo=False, pool_pre_ping=True)


def ensure_tables(engine) -> None:  # noqa: ANN001
    """Create all tables if they do not exist (safe no-op when they do)."""
    Base.metadata.create_all(engine)


def seed_pois(engine, city_name: str, pois: list[dict[str, Any]]) -> None:
    """Insert POI records into the database.

    Args:
        engine: Synchronous SQLAlchemy engine.
        city_name: City label used for log output.
        pois: List of POI dicts.  Each dict must contain at minimum:
            name, category, lng (float), lat (float).
            Optional keys: rating, tags, description, opening_hours,
            avg_visit_duration, review_count, extra_data.
    """
    with Session(engine) as session:
        for p in pois:
            wkt = f"POINT({p['lng']} {p['lat']})"
            poi = POI(
                name=p["name"],
                category=p["category"],
                city=city_name,
                location=WKTElement(wkt, srid=4326),
                rating=p.get("rating"),
                tags=p.get("tags"),
                description=p.get("description"),
                opening_hours=p.get("opening_hours"),
                avg_visit_duration=p.get("avg_visit_duration"),
                review_count=p.get("review_count"),
                extra_data=p.get("extra_data"),
            )
            session.add(poi)
        session.commit()

    print(f"  Seeded {len(pois)} POIs for {city_name}")


def check_existing(engine, city_name: str) -> bool:
    """Return True and print a message if POIs already exist for the city."""
    insp = inspect(engine)
    if "pois" not in insp.get_table_names():
        return False
    with Session(engine) as session:
        count = session.query(POI).filter(POI.city == city_name).count()
    if count > 0:
        print(f"  Skipping {city_name}: {count} POIs already exist")
        return True
    return False
