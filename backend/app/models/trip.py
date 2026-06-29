"""Trip, TripDay, TripDayPOI models with cascading deletes."""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.poi import Base

if TYPE_CHECKING:
    from app.models.user import User


class Trip(Base):
    """A travel trip plan."""

    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft", index=True
    )
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="trips")
    days: Mapped[list["TripDay"]] = relationship(
        "TripDay",
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="TripDay.day_number",
    )

    def __repr__(self) -> str:
        return f"<Trip(id={self.id}, title={self.title}, city={self.city})>"


class TripDay(Base):
    """A single day within a trip."""

    __tablename__ = "trip_days"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships
    trip: Mapped["Trip"] = relationship("Trip", back_populates="days")
    pois: Mapped[list["TripDayPOI"]] = relationship(
        "TripDayPOI",
        back_populates="trip_day",
        cascade="all, delete-orphan",
        order_by="TripDayPOI.sort_order",
    )

    def __repr__(self) -> str:
        return f"<TripDay(id={self.id}, trip_id={self.trip_id}, day={self.day_number})>"


class TripDayPOI(Base):
    """A POI scheduled for a specific trip day."""

    __tablename__ = "trip_day_pois"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trip_day_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("trip_days.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    poi_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pois.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    arrival_time: Mapped[str] = mapped_column(String(10), nullable=True)
    departure_time: Mapped[str] = mapped_column(String(10), nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships
    trip_day: Mapped["TripDay"] = relationship("TripDay", back_populates="pois")

    def __repr__(self) -> str:
        return f"<TripDayPOI(id={self.id}, poi_id={self.poi_id}, order={self.sort_order})>"
