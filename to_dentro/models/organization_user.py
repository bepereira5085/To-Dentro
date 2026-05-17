from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .user import User
    from .organization import Organization

class OrganizationUser(db.Model):
    __tablename__ = 'organization_users'
    __table_args__ = {'extend_existing': True}

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(50))

    user: Mapped["User"] = relationship(
        "User", back_populates="organizations"
    )
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="users"
    )
