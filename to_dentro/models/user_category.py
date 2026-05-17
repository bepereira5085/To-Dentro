from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .category import Category
    from .user import User


class UserCategory(db.Model):
    __tablename__ = "user_categories"
    __table_args__ = {"extend_existing": True}

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )

    user: Mapped["User"] = relationship("User", back_populates="categories")
    category: Mapped["Category"] = relationship("Category", back_populates="user_categories")
