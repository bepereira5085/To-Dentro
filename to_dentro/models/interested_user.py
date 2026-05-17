from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .event import Event
    from .user import User

class InterestedUser(db.Model):
    __tablename__ = 'interested_users'
    __table_args__ = {'extend_existing': True}

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(
        "User", back_populates="interested_events"
    )
    event: Mapped["Event"] = relationship(
        "Event", back_populates="interested_users"
    )
