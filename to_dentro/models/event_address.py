from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .event_occurrence import EventOccurrence
    from .address import Address

class EventAddress(db.Model):
    __tablename__ = 'events_addresses'
    __table_args__ = {'extend_existing': True}

    event_occurrence_id: Mapped[int] = mapped_column(
        ForeignKey("event_occurrences.id", ondelete="CASCADE"), primary_key=True
    )
    address_id: Mapped[int] = mapped_column(
        ForeignKey("addresses.id", ondelete="CASCADE"), primary_key=True
    )

    occurrence: Mapped["EventOccurrence"] = relationship(
        "EventOccurrence", back_populates="addresses"
    )
    address: Mapped["Address"] = relationship(
        "Address", back_populates="event_addresses"
    )
