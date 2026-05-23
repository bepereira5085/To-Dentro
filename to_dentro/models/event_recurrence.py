import enum
from typing import List, TYPE_CHECKING
from datetime import date
from sqlalchemy import ForeignKey, Integer, Date, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .event import Event
    from .event_recurrence_weekday import EventRecurrenceWeekday

class RecurrenceTypes(enum.Enum):
    DAILY = 'Diário'
    WEEKLY = 'Semanal'
    MONTHLY = 'Mensal'
    YEARLY = 'Anual'

class WeeksInterval(enum.Enum):
    ONE = 1 # intervalo de 1 semana (quinzenal)
    TWO = 2 # intervalo de 2 semanas (primeira semana - quarta semana)

class EventRecurrence(db.Model):
    __tablename__ = 'event_recurrences'
    __table_args__ = (
        CheckConstraint('day_of_month >= 1 AND day_of_month <= 31', name='check_day_of_month_range'),
        {'extend_existing': True}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE")
    )
    type: Mapped[RecurrenceTypes] = mapped_column(db.Enum(RecurrenceTypes))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)
    weeks_interval: Mapped[WeeksInterval] = mapped_column(db.Enum(WeeksInterval), nullable=True)
    day_of_month: Mapped[int] = mapped_column(Integer, nullable=True)

    event: Mapped["Event"] = relationship(
        "Event", back_populates="recurrences"
    )

    weekdays: Mapped[List["EventRecurrenceWeekday"]] = relationship(
        "EventRecurrenceWeekday", back_populates="recurrence", cascade="all, delete-orphan"
    )

    @validates('type')
    def validate_type(self, key, value):
        if isinstance(value, str):
            try:
                return RecurrenceTypes[value]
            except KeyError:
                raise ValueError(f"'{value}' não é um valor válido para RecurrenceTypes")
        return value

    @validates('weeks_interval')
    def validate_weeks_interval(self, key, value):
        if value is not None:
            if isinstance(value, str):
                try:
                    return WeeksInterval[value]
                except KeyError:
                    raise ValueError(f"'{value}' não é um valor válido para WeeksInterval")
        return value

    @validates('day_of_month')
    def validate_day_of_month(self, key, value):
        if value is not None:
            if not (1 <= value <= 31):
                raise ValueError("O dia do mês deve estar entre 1 e 31")
        return value
