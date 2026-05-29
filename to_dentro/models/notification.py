import enum
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import ForeignKey, Integer, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .user import User
    from .event_occurrence import EventOccurrence
    from .hangout_poll import HangoutPoll

class NotificationType(enum.Enum):
    FOLLOW = 'follow'
    EVENT_INTERESTED = 'event_interested'
    EVENT_REMINDER = 'event_reminder'
    EVENT_STARTING_SOON = 'event_starting_soon'
    EVENT_CANCELLED = 'event_cancelled'
    EVENT_UPDATED = 'event_updated'
    EVENT_LOCATION_CHANGED = 'event_location_changed'
    EVENT_NEW_OCCURRENCE = 'event_new_occurrence'
    EVENT_OCCURRENCE_CANCELLED = 'event_occurrence_cancelled'
    FRIEND_JOINED_EVENT = 'friend_joined_event'
    ORGANIZATION_INVITE = 'organization_invite'
    ORGANIZATION_ROLE_CHANGED = 'organization_role_changed'
    EVENT_CAPACITY_REACHED = 'event_capacity_reached'
    EVENT_CAPACITY_AVAILABLE = 'event_capacity_available'
    EVENT_CREATED = 'event_created'
    EVENT_APPROVED = 'event_approved'
    EVENT_REJECTED = 'event_rejected'
    EVENT_IMAGE_ADDED = 'event_image_added'
    EVENT_RECOMMENDATION = 'event_recommendation'
    POLL_INVITATION = 'poll_invitation'
    SYSTEM = 'system'

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
    type: Mapped[NotificationType] = mapped_column(db.Enum(NotificationType))

    actor: Mapped["User"] = relationship(
        "User", foreign_keys=[actor_user_id], back_populates="notifications_sent"
    )
    recipient: Mapped["User"] = relationship(
        "User", foreign_keys=[recipient_user_id], back_populates="notifications_received"
    )
    event_occurrence: Mapped[Optional["EventOccurrence"]] = relationship(
        "EventOccurrence"
    )
    poll_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("hangout_polls.id", ondelete="CASCADE"), nullable=True
    )
    poll: Mapped[Optional["HangoutPoll"]] = relationship(
        "HangoutPoll"
    )

    @validates('type')
    def validate_type(self, key, value):
        if isinstance(value, str):
            try:
                return NotificationType[value]
            except KeyError:
                raise ValueError(f"'{value}' não é um valor válido para NotificationType")
        return value
