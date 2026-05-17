import os

from dotenv import load_dotenv


def init_app(app):
    load_dotenv(".env.dev")
    for key, value in os.environ.items():
        if key.startswith("FLASK_") or key in [
            "SECRET_KEY",
            "SQLALCHEMY_DATABASE_URI",
            "SQLALCHEMY_TRACK_MODIFICATIONS",
            "DEBUG_TB_INTERCEPT_REDIRECTS",
        ]:
            app.config[key] = value
