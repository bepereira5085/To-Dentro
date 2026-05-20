import enum
from typing import TYPE_CHECKING, List

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from to_dentro.ext.db import db

if TYPE_CHECKING:
    from .event_category import EventCategories
    from .user_category import UserCategory

class Categories(enum.Enum):
    CONCERT = 'Show Musical'
    TECHNICAL_VISIT = 'Visita Técnica'
    PARTY = 'Festa'
    CONFERENCE = 'Conferência'
    WORKSHOP = 'Workshop'
    MEETUP = 'Meetup'
    NETWORKING = 'Networking'
    HACKATHON = 'Hackathon'
    SPORTS = 'Esporte'
    CYCLING = 'Ciclismo'
    RUNNING = 'Corrida'
    HIKING = 'Trilha'
    CAMPING = 'Camping'
    FESTIVAL = 'Festival'
    FAIR = 'Feira'
    EXHIBITION = 'Exposição'
    THEATER = 'Teatro'
    CINEMA = 'Cinema'
    STAND_UP = 'Stand-up Comedy'
    GASTRONOMY = 'Gastronomia'
    BARBECUE = 'Churrasco'
    WINE_TASTING = 'Degustação de Vinhos'
    COFFEE_MEETUP = 'Encontro de Café'
    GAMING = 'Games'
    BOARD_GAMES = 'Jogos de Tabuleiro'
    ESPORTS = 'eSports'
    EDUCATION = 'Educação'
    LANGUAGE_EXCHANGE = 'Intercâmbio de Idiomas'
    STUDY_GROUP = 'Grupo de Estudos'
    SCIENCE = 'Ciência'
    TECHNOLOGY = 'Tecnologia'
    AI = 'Inteligência Artificial'
    BUSINESS = 'Negócios'
    ENTREPRENEURSHIP = 'Empreendedorismo'
    MARKETING = 'Marketing'
    DESIGN = 'Design'
    PROGRAMMING = 'Programação'
    OPEN_SOURCE = 'Open Source'
    RELIGIOUS = 'Religioso'
    VOLUNTEERING = 'Voluntariado'
    SOCIAL = 'Social'
    DATING = 'Encontro'
    PETS = 'Pets'
    HEALTH = 'Saúde'
    FITNESS = 'Fitness'
    YOGA = 'Yoga'
    MEDITATION = 'Meditação'
    DANCE = 'Dança'
    PHOTOGRAPHY = 'Fotografia'
    ART = 'Arte'
    BOOK_CLUB = 'Clube do Livro'

class Category(db.Model):
    __tablename__ = "categories"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[Categories] = mapped_column(db.Enum(Categories))

    user_categories: Mapped[List["UserCategory"]] = relationship(
        "UserCategory", back_populates="category", cascade="all, delete-orphan"
    )
    event_categories: Mapped[List["EventCategories"]] = relationship(
        "EventCategory", back_populates="category", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Category {self.name}>"
