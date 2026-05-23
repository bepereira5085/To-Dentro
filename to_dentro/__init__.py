from flask import Flask

from to_dentro import models
from to_dentro.ext import config, db, migrate, debugtoolbar, wtf, cli, auth
from to_dentro.views.main import main_bp


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder='../static')

    config.init_app(app)

    db.init_app(app)
    migrate.init_app(app)
    cli.init_app(app)
    wtf.init_app(app)
    debugtoolbar.init_app(app)
    auth.init_app(app)

    models.init_app(app)
    app.register_blueprint(main_bp)

    return app
