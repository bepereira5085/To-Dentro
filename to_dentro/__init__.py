from flask import Flask

from to_dentro import models
from to_dentro.ext import config, db, debugtoolbar, wtf
from to_dentro.views import main


def create_app():
    app = Flask(__name__, template_folder="../templates")

    config.init_app(app)

    db.init_app(app)
    wtf.init_app(app)
    debugtoolbar.init_app(app)

    models.init_app(app)
    main.init_app(app)

    return app
