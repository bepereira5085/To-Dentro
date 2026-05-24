import os

from dotenv import load_dotenv

BOOL_KEYS = {
    "SQLALCHEMY_TRACK_MODIFICATIONS",
    "DEBUG_TB_INTERCEPT_REDIRECTS",
    "FLASK_DEBUG",
}


def _parse_value(key, value):
    if key in BOOL_KEYS:
        return value.strip().lower() not in ("false", "0", "no", "")
    return value


def init_app(app):
    load_dotenv(".env.dev")
    for key, value in os.environ.items():
        if key.startswith("FLASK_") or key.startswith("CLOUDINARY_") or key in [
            "SECRET_KEY",
            "SQLALCHEMY_DATABASE_URI",
            "SQLALCHEMY_TRACK_MODIFICATIONS",
            "DEBUG_TB_INTERCEPT_REDIRECTS",
        ]:
            app.config[key] = _parse_value(key, value)
