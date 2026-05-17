from flask import Blueprint, render_template

bp = Blueprint('main', __name__)

@bp.route('/')
def index ():
    contexto = {
        'titulo_app': 'Tô Dentro!',
        'mensagem': 'Bem-vindo ao aplicativo de eventos',
        'recursos': [
            'Divulgação de eventos',
            'Divulgação de atividades',
            'Saiba em que evento seus amigos estão dentro'
        ]
    }

    return render_template('index.html', **contexto)

def init_app (app):
    app.register_blueprint(bp)