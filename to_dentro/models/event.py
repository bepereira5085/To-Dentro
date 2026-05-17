from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .event_category import EventCategories
    from .event_image import EventImage
    from .event_occurrence import EventOccurrence
    from .event_recurrence import EventRecurrence
    from .interested_user import InterestedUser
    from .organization import Organization


class Event(db.Model):
    __tablename__ = "events"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(2000))
    is_recurrent: Mapped[bool] = mapped_column(Boolean, default=False)

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="events"
    )

    interested_users: Mapped[List["InterestedUser"]] = relationship(
        "InterestedUser", back_populates="event", cascade="all, delete-orphan"
    )

    occurrences: Mapped[List["EventOccurrence"]] = relationship(
        "EventOccurrence", back_populates="event", cascade="all, delete-orphan"
    )

    images: Mapped[List["EventImage"]] = relationship(
        "EventImage", back_populates="event", cascade="all, delete-orphan"
    )

    recurrences: Mapped[List["EventRecurrence"]] = relationship(
        "EventRecurrence", back_populates="event", cascade="all, delete-orphan"
    )

    tags: Mapped[List["EventCategories"]] = relationship(
        "EventTag", back_populates="event", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Event {self.name}>"
