from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from werkzeug.datastructures import MultiDict
from flask_login import login_user, logout_user, login_required, current_user
from to_dentro.forms.main import LoginForm
from to_dentro.forms.register import RegisterForm
from to_dentro.models.user import User, UserType
from to_dentro.models.address import Address
from to_dentro.models.user_address import UserAddress
from to_dentro.ext.db import db
import re

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('main/index.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        form = LoginForm()
        if form.validate_on_submit():
            email_digitado = form.email.data
            senha_digitada = form.password.data

            usuario = User.query.filter_by(email=email_digitado).first()

            if usuario and usuario.check_password(senha_digitada):
                login_user(usuario)
                return redirect(url_for('main.index'))
            else:
                session['login_form_data'] = request.form.to_dict()
                session['login_form_errors'] = {'password': ["E-mail ou senha incorretos. Tente novamente."]}
                return redirect(url_for('main.login'))
        else:
            session['login_form_data'] = request.form.to_dict()
            session['login_form_errors'] = form.errors
            return redirect(url_for('main.login'))

    form_data = session.pop('login_form_data', None)
    form_errors = session.pop('login_form_errors', None)

    if form_data:
        form = LoginForm(formdata=MultiDict(form_data))
        if form_errors:
            for field_name, errors in form_errors.items():
                field = getattr(form, field_name, None)
                if field and errors:
                    field.errors = [errors[0]]
    else:
        form = LoginForm()

    return render_template('main/login.html', form=form)


@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        form = RegisterForm()
        if form.validate_on_submit():
            if User.query.filter_by(email=form.email.data.strip().lower()).first():
                session['register_form_data'] = request.form.to_dict()
                session['register_form_errors'] = {'email': ["Este e-mail já está cadastrado. Tente fazer login ou informe outro e-mail."]}
                return redirect(url_for('main.register'))

            user_type = UserType.ORGANIZER if form.user_type.data == "ORGANIZER" else UserType.REGULAR
            cpf = form.cpf.data if user_type == UserType.ORGANIZER else None
            phone = form.phone.data

            user = User(
                name=form.name.data.strip(),
                email=form.email.data.strip().lower(),
                phone=phone,
                birth_date=form.birth_date.data,
                cpf=cpf,
                type=user_type,
            )
            user.set_password(form.password.data)

            try:
                db.session.add(user)
                db.session.flush()

                cep_value = form.cep.data if form.cep.data else None
                if cep_value:
                    address = Address(
                        street="",
                        number="",
                        city="",
                        state="",
                        cep=cep_value,
                        country="Brasil",
                    )
                    db.session.add(address)
                    db.session.flush()

                    user_address = UserAddress(user_id=user.id, address_id=address.id)
                    db.session.add(user_address)

                db.session.commit()
                login_user(user)
                flash("Conta criada com sucesso! Bem-vindo ao Tô Dentro!", "is-success")
                return redirect(url_for('main.index'))
            except Exception:
                db.session.rollback()
                flash("Ocorreu um erro ao criar sua conta. Tente novamente.", "is-danger")
                session['register_form_data'] = request.form.to_dict()
                return redirect(url_for('main.register'))
        else:
            session['register_form_data'] = request.form.to_dict()
            session['register_form_errors'] = form.errors
            return redirect(url_for('main.register'))

    form_data = session.pop('register_form_data', None)
    form_errors = session.pop('register_form_errors', None)

    if form_data:
        form = RegisterForm(formdata=MultiDict(form_data))
        if form_errors:
            for field_name, errors in form_errors.items():
                field = getattr(form, field_name, None)
                if field and errors:
                    field.errors = [errors[0]]
    else:
        form = RegisterForm()

    return render_template('main/register.html', form=form)


@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@main_bp.app_context_processor
def inject_global_variables():
    return {
        'titulo_app': 'Tô Dentro',
        'mensagem': 'A plataforma de eventos comunitários e gratuitos',
        'recursos': [
            'Encontre eventos perto de você',
            'Crie e divulgue seus próprios eventos',
            'Acompanhe seus produtores favoritos',
            'Receba notificações personalizadas'
        ]
    }