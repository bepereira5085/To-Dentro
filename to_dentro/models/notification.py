from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import ForeignKey, String, Integer, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .user import User
    from .event_occurrence import EventOccurrence

class Notification(db.Model):
    __tablename__ = 'notifications'
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    recipient_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    event_occurrence_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("event_occurrences.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True), server_default=func.now()
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    type: Mapped[str] = mapped_column(String(50))

    actor: Mapped["User"] = relationship(
        "User", foreign_keys=[actor_user_id], back_populates="notifications_sent"
    )
    recipient: Mapped["User"] = relationship(
        "User", foreign_keys=[recipient_user_id], back_populates="notifications_received"
    )
    event_occurrence: Mapped[Optional["EventOccurrence"]] = relationship(
        "EventOccurrence"
    )
