import enum
import re
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy import func, Integer
from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .follows import Follow
    from .organization_user import OrganizationUser
    from .interested_user import InterestedUser
    from .user_category import UserCategory
    from .user_address import UserAddress
    from .notification import Notification


class UserType(enum.Enum):
    REGULAR = "Regular"
    ORGANIZER = "Organizer"


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(db.String(50))
    email: Mapped[str] = mapped_column(db.String(100), unique=True, index=True)
    password: Mapped[str] = mapped_column(db.String(255))
    cpf: Mapped[Optional[str]] = mapped_column(
        db.String(11), unique=True, index=True, nullable=True
    )
    phone: Mapped[str] = mapped_column(db.String(11))

    type: Mapped[UserType] = mapped_column(db.Enum(UserType), default=UserType.REGULAR)

    created_at: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True), server_default=func.now()
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        db.DateTime(timezone=True), nullable=True
    )

    organizations: Mapped[List["OrganizationUser"]] = relationship(
        "OrganizationUser", back_populates="user", cascade="all, delete-orphan"
    )
    interested_events: Mapped[List["InterestedUser"]] = relationship(
        "InterestedUser", back_populates="user", cascade="all, delete-orphan"
    )
    following: Mapped[List["Follow"]] = relationship(
        "Follow",
        foreign_keys="[Follow.follower_id]",
        back_populates="follower",
        cascade="all, delete-orphan",
    )
    followers: Mapped[List["Follow"]] = relationship(
        "Follow",
        foreign_keys="[Follow.following_id]",
        back_populates="following",
        cascade="all, delete-orphan",
    )
    categories: Mapped[List["UserCategory"]] = relationship(
        "UserCategory", back_populates="user", cascade="all, delete-orphan"
    )
    addresses: Mapped[List["UserAddress"]] = relationship(
        "UserAddress", back_populates="user", cascade="all, delete-orphan"
    )
    notifications_sent: Mapped[List["Notification"]] = relationship(
        "Notification",
        foreign_keys="[Notification.actor_user_id]",
        back_populates="actor",
        cascade="all, delete-orphan",
    )
    notifications_received: Mapped[List["Notification"]] = relationship(
        "Notification",
        foreign_keys="[Notification.recipient_user_id]",
        back_populates="recipient",
        cascade="all, delete-orphan",
    )

    @validates("cpf")
    def validate_cpf(self, key, cpf):
        if cpf is not None:
            if len(cpf) != 11:
                raise ValueError("O CPF deve conter exatamente 11 dígitos.")
            if not cpf.isdigit():
                raise ValueError("O CPF deve conter apenas números.")
        return cpf

    @validates("phone")
    def validate_phone(self, key, phone):
        if not phone or len(phone) < 10:
            raise ValueError("O telefone deve conter pelo menos 10 dígitos.")
        if not phone.isdigit():
            raise ValueError("O telefone deve conter apenas números.")
        return phone

    @validates("email")
    def validate_email(self, key, value):
        if not re.match(r"[^@]+@[^@]+\.[^@]+", value):
            raise ValueError("Formato de email inválido.")
        return value

    @validates("type")
    def validate_type(self, key, user_type):
        if isinstance(user_type, str):
            try:
                return UserType[user_type]
            except KeyError:
                raise ValueError(f"'{user_type}' não é um tipo de utilizador válido.")
        return user_type

    def __repr__(self) -> str:
        return f"<User {self.name} - {self.email} [{self.type.value if hasattr(self.type, 'value') else self.type}]>"
