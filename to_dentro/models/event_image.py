from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .event import Event


class EventImage(db.Model):
    __tablename__ = "event_images"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(255))

    event: Mapped["Event"] = relationship("Event", back_populates="images")
