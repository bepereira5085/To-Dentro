from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .event_recurrence import EventRecurrence

# TODO: fazer enum de weekdays

class EventRecurrenceWeekday(db.Model):
    __tablename__ = 'event_recurrence_weekdays'
    __table_args__ = {'extend_existing': True}

    recurrence_id: Mapped[int] = mapped_column(
        ForeignKey("event_recurrences.id", ondelete="CASCADE"), primary_key=True
    )
    weekday: Mapped[int] = mapped_column(Integer, primary_key=True)

    recurrence: Mapped["EventRecurrence"] = relationship(
        "EventRecurrence", back_populates="weekdays"
    )
