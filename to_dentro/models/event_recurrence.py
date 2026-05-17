from typing import List, TYPE_CHECKING
from datetime import date
from sqlalchemy import ForeignKey, String, Integer, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .event import Event
    from .event_recurrence_weekday import EventRecurrenceWeekday

#  TODO: fazer enum de recurrence

class EventRecurrence(db.Model):
    __tablename__ = 'event_recurrences'
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE")
    )
    type: Mapped[str] = mapped_column(String(50))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)
    weeks_interval: Mapped[int] = mapped_column(Integer, nullable=True)
    day_of_month: Mapped[int] = mapped_column(Integer, nullable=True)

    event: Mapped["Event"] = relationship(
        "Event", back_populates="recurrences"
    )

    weekdays: Mapped[List["EventRecurrenceWeekday"]] = relationship(
        "EventRecurrenceWeekday", back_populates="recurrence", cascade="all, delete-orphan"
    )
