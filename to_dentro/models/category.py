from typing import TYPE_CHECKING, List

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .event_category import EventCategories
    from .user_category import UserCategory


class Category(db.Model):
    __tablename__ = "categories"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)

    user_categories: Mapped[List["UserCategory"]] = relationship(
        "UserCategory", back_populates="category", cascade="all, delete-orphan"
    )
    event_categories: Mapped[List["EventCategories"]] = relationship(
        "EventCategory", back_populates="category", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Category {self.name}>"
