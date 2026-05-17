from typing import List, TYPE_CHECKING
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .user_address import UserAddress
    from .event_address import EventAddress

class Address(db.Model):
    __tablename__ = 'addresses'
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    street: Mapped[str] = mapped_column(String(200))
    number: Mapped[str] = mapped_column(String(10))
    city: Mapped[str] = mapped_column(String(50))
    state: Mapped[str] = mapped_column(String(50))
    cep: Mapped[str] = mapped_column(String(8))
    country: Mapped[str] = mapped_column(String(50))

    user_addresses: Mapped[List["UserAddress"]] = relationship(
        "UserAddress", back_populates="address", cascade="all, delete-orphan"
    )

    event_addresses: Mapped[List["EventAddress"]] = relationship(
        "EventAddress", back_populates="address", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Address {self.street}, {self.number} - {self.city}>"
