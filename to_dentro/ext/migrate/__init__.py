from flask_migrate import Migrate
from to_dentro.ext.db import db

migrate = Migrate()


def init_app(app):
    migrate.init_app(app, db)
