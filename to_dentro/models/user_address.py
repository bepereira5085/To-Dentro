from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .user import User
    from .address import Address

class UserAddress(db.Model):
    __tablename__ = 'users_addresses'
    __table_args__ = {'extend_existing': True}

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    address_id: Mapped[int] = mapped_column(
        ForeignKey("addresses.id", ondelete="CASCADE"), primary_key=True
    )

    user: Mapped["User"] = relationship(
        "User", back_populates="addresses"
    )
    address: Mapped["Address"] = relationship(
        "Address", back_populates="user_addresses"
    )
