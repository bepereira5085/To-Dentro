from typing import List, TYPE_CHECKING
from datetime import date, time
from sqlalchemy import ForeignKey, String, Integer, Date, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .event import Event
    from .event_address import EventAddress


class EventOccurrence(db.Model):
    __tablename__ = "event_occurrences"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    observations: Mapped[str] = mapped_column(String(500), nullable=True)
    interested_count: Mapped[int] = mapped_column(Integer, default=0)
    start_date: Mapped[date] = mapped_column(Date)
    duration_days: Mapped[int] = mapped_column(Integer, default=1)
    start_time: Mapped[time] = mapped_column(Time)
    duration_time: Mapped[time] = mapped_column(Time, nullable=True)

    event: Mapped["Event"] = relationship("Event", back_populates="occurrences")

    addresses: Mapped[List["EventAddress"]] = relationship(
        "EventAddress", back_populates="occurrence", cascade="all, delete-orphan"
    )

    @validates("interested_count")
    def validate_interested_count(self, key, value):
        if value < 0:
            raise ValueError("A quantidade de interessados não pode ser negativa")
        return value

    @validates("duration_days")
    def validate_duration_days(self, key, value):
        if value < 1:
            raise ValueError("A duração do evento deve ser de pelo menos 1 dia")
        return value
