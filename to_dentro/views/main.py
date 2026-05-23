from flask import Blueprint, render_template, redirect, url_for, flash
from to_dentro.forms.main import LoginForm
from to_dentro.models.user import User

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('main/index.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        email_digitado = form.email.data
        senha_digitada = form.password.data

        usuario = User.query.filter_by(email=email_digitado).first()

        if usuario and usuario.check_password(senha_digitada):
            flash("Login realizado com sucesso! Bem-vindo ao Tô Dentro!", "is-success")
            return redirect(url_for('main.index'))
        else:
            flash("E-mail ou senha incorretos. Tente novamente.", "is-danger")

    return render_template('main/login.html', form=form)