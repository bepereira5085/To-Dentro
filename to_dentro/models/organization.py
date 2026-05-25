import re
from typing import List, TYPE_CHECKING, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy import String, Integer
from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .organization_user import OrganizationUser
    from .event import Event


class Organization(db.Model):
    __tablename__ = "organizations"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cnpj: Mapped[str] = mapped_column(String(14), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    photo_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    users: Mapped[List["OrganizationUser"]] = relationship(
        "OrganizationUser", back_populates="organization", cascade="all, delete-orphan"
    )

    events: Mapped[List["Event"]] = relationship(
        "Event", back_populates="organization", cascade="all, delete-orphan"
    )

    @validates("cnpj")
    def validate_cnpj(self, key, value):
        if value is not None:
            if len(value) != 14:
                raise ValueError("O CNPJ deve ter exatamente 14 caracteres")
            if not value.isdigit():
                raise ValueError("O CNPJ deve conter apenas números")
        return value

    @validates("email")
    def validate_email(self, key, value):
        if not re.match(r"[^@]+@[^@]+\.[^@]+", value):
            raise ValueError("Formato de email inválido")
        return value

    def __repr__(self) -> str:
        return f"<Organization {self.name} - {self.cnpj}>"
