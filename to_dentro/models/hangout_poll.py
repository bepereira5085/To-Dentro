import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .user import User
    from .event import Event


class HangoutPoll(db.Model):
    __tablename__ = "hangout_polls"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    creator: Mapped["User"] = relationship("User")
    options: Mapped[List["HangoutPollOption"]] = relationship(
        "HangoutPollOption", back_populates="poll", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<HangoutPoll {self.title} ({self.uuid})>"


class HangoutPollOption(db.Model):
    __tablename__ = "hangout_poll_options"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey("hangout_polls.id", ondelete="CASCADE"))
    event_id: Mapped[Optional[int]] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=True)
    custom_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    poll: Mapped["HangoutPoll"] = relationship("HangoutPoll", back_populates="options")
    event: Mapped[Optional["Event"]] = relationship("Event")
    votes: Mapped[List["HangoutPollVote"]] = relationship(
        "HangoutPollVote", back_populates="option", cascade="all, delete-orphan"
    )

    @property
    def title(self) -> str:
        if self.event:
            return self.event.name
        return self.custom_title or "Opção sem título"

    def __repr__(self) -> str:
        return f"<HangoutPollOption {self.title}>"


class HangoutPollVote(db.Model):
    __tablename__ = "hangout_poll_votes"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    poll_option_id: Mapped[int] = mapped_column(ForeignKey("hangout_poll_options.id", ondelete="CASCADE"))
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    voter_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    option: Mapped["HangoutPollOption"] = relationship("HangoutPollOption", back_populates="votes")
    user: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        name = self.user.name if self.user else self.voter_name or "Anônimo"
        return f"<HangoutPollVote by {name}>"
