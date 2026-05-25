from flask import Flask

from to_dentro import models
from to_dentro.ext import config, db, migrate, debugtoolbar, wtf, cli, auth, cloudinary, admin
from to_dentro.views.main import main_bp


def create_app(test_config=None):
    app = Flask(__name__, template_folder="../templates", static_folder='../static')

    config.init_app(app)

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app)
    cli.init_app(app)
    wtf.init_app(app)
    debugtoolbar.init_app(app)
    auth.init_app(app)
    cloudinary.init_app(app)
    admin.init_app(app)

    models.init_app(app)
    app.register_blueprint(main_bp)

    return app
