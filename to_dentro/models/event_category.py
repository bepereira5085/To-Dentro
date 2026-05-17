from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .category import Category
    from .event import Event


class EventCategories(db.Model):
    __tablename__ = "events_categories"
    __table_args__ = {"extend_existing": True}

    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )

    event: Mapped["Event"] = relationship("Event", back_populates="categories")
    category: Mapped["Category"] = relationship("Category", back_populates="event_categories")
