"""POI model with PostGIS geometry and shared Base class."""

from datetime import datetime

from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape
from sqlalchemy import ARRAY, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all models."""

    pass


class POI(Base):
    """Point of Interest with spatial data."""

    __tablename__ = "pois"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    location = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    tags: Mapped[list] = mapped_column(ARRAY(String), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    opening_hours: Mapped[str] = mapped_column(String(255), nullable=True)
    avg_visit_duration: Mapped[int] = mapped_column(Integer, nullable=True)
    review_count: Mapped[int] = mapped_column(Integer, nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def to_dict(self) -> dict:
        """Convert POI to dictionary."""
        result = {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "city": self.city,
            "rating": self.rating,
            "tags": self.tags,
            "description": self.description,
            "opening_hours": self.opening_hours,
            "avg_visit_duration": self.avg_visit_duration,
            "review_count": self.review_count,
            "extra_data": self.extra_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if self.location:
            point = to_shape(self.location)
            result["location"] = {"lng": point.x, "lat": point.y}
        return result
