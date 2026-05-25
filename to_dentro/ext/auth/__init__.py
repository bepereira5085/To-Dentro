from flask_login import LoginManager
from to_dentro.models.user import User

login_manager = LoginManager()

def init_app(app):
    login_manager.init_app(app)

    login_manager.login_view = "main.login"
    login_manager.login_message = "Por favor, inicie sessão para acessar esta página."
    login_manager.login_message_category = "is-warning"

    ## Linha extremamente crítica. NAO SUBIR COM PROTEÇÂO DESATIVADA
    login_manager.session_protection = None


    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))