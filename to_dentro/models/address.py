from typing import List, TYPE_CHECKING, Optional
from sqlalchemy import String, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .user_address import UserAddress
    from .event_address import EventAddress


class Address(db.Model):
    __tablename__ = "addresses"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    street: Mapped[str] = mapped_column(String(200))
    number: Mapped[str] = mapped_column(String(10))
    city: Mapped[str] = mapped_column(String(50))
    state: Mapped[str] = mapped_column(String(50))
    cep: Mapped[str] = mapped_column(String(8))
    country: Mapped[str] = mapped_column(String(50))
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    user_addresses: Mapped[List["UserAddress"]] = relationship(
        "UserAddress", back_populates="address", cascade="all, delete-orphan"
    )

    event_addresses: Mapped[List["EventAddress"]] = relationship(
        "EventAddress", back_populates="address", cascade="all, delete-orphan"
    )

    @validates("cep")
    def validate_cep(self, key, value):
        if value is not None:
            if len(value) != 8:
                raise ValueError("O CEP deve ter exatamente 8 caracteres")
            if not value.isdigit():
                raise ValueError("O CEP deve conter apenas números")
        return value

    def __repr__(self) -> str:
        return f"<Address {self.street}, {self.number} - {self.city}>"
