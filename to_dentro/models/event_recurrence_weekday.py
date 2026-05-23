import enum
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .event_recurrence import EventRecurrence

class WeekDays(enum.Enum):
    SUNDAY = 1
    MONDAY = 2
    TUESDAY = 3
    WEDNESDAY = 4
    THURSDAY = 5
    FRIDAY = 6
    SATURDAY = 7

class EventRecurrenceWeekday(db.Model):
    __tablename__ = 'event_recurrence_weekdays'
    __table_args__ = {'extend_existing': True}

    recurrence_id: Mapped[int] = mapped_column(
        ForeignKey("event_recurrences.id", ondelete="CASCADE"), primary_key=True
    )
    weekday: Mapped[WeekDays] = mapped_column(db.Enum(WeekDays), primary_key=True)

    recurrence: Mapped["EventRecurrence"] = relationship(
        "EventRecurrence", back_populates="weekdays"
    )

    @validates('weekday')
    def validate_weekday(self, key, value):
        if isinstance(value, str):
            try:
                return WeekDays[value]
            except KeyError:
                raise ValueError(f"'{value}' não é um valor válido para WeekDays")
        return value
