import re
from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, HiddenField, DateField
from wtforms.validators import (
    DataRequired, Email, Length, ValidationError, Optional
)


def strip_non_digits(value):
    if value:
        return re.sub(r"\D", "", value)
    return value


def validate_strong_password(form, field):
    password = field.data or ""
    errors = []
    if not re.search(r"[A-Z]", password):
        errors.append("uma letra maiúscula")
    if not re.search(r"[a-z]", password):
        errors.append("uma letra minúscula")
    if not re.search(r"\d", password):
        errors.append("um número")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?~`]", password):
        errors.append("um caractere especial")
    if errors:
        raise ValidationError(f"A senha deve conter pelo menos: {', '.join(errors)}.")


def validate_birth_date(form, field):
    if field.data is None:
        return
    today = date.today()
    if field.data >= today:
        raise ValidationError("A data de nascimento deve ser anterior à data atual.")
    age = today.year - field.data.year - (
        (today.month, today.day) < (field.data.month, field.data.day)
    )
    if age < 16:
        raise ValidationError("Você precisa ter pelo menos 16 anos para usar o Tô Dentro!.")


def validate_cpf_if_organizer(form, field):
    if form.user_type.data == "ORGANIZER":
        cpf = field.data or ""
        if not cpf:
            raise ValidationError("O CPF é obrigatório para produtores.")
        if len(cpf) != 11:
            raise ValidationError("O CPF deve conter exatamente 11 dígitos.")
        if not cpf.isdigit():
            raise ValidationError("O CPF deve conter apenas números.")


class RegisterForm(FlaskForm):
    user_type = HiddenField("Tipo de usuário", default="REGULAR")

    name = StringField(
        "Nome completo",
        validators=[
            DataRequired(message="O nome é obrigatório."),
            Length(max=50, message="O nome deve ter no máximo 50 caracteres."),
        ],
    )

    email = StringField(
        "Email",
        validators=[
            DataRequired(message="O e-mail é obrigatório."),
            Email(message="Por favor, insira um e-mail válido."),
            Length(max=100, message="O e-mail deve ter no máximo 100 caracteres."),
        ],
    )

    password = PasswordField(
        "Senha",
        validators=[
            DataRequired(message="A senha é obrigatória."),
            Length(min=8, message="A senha deve ter no mínimo 8 caracteres."),
            validate_strong_password,
        ],
    )

    phone = StringField(
        "Telefone",
        validators=[
            DataRequired(message="O telefone é obrigatório."),
            Length(min=10, max=11, message="O telefone deve ter entre 10 e 11 dígitos."),
        ],
        filters=[strip_non_digits],
    )

    cep = StringField(
        "CEP",
        validators=[
            DataRequired(message="O CEP é obrigatório."),
            Length(min=8, max=8, message="O CEP deve ter exatamente 8 números."),
        ],
        filters=[strip_non_digits],
    )

    birth_date = DateField(
        "Data de nascimento",
        format="%Y-%m-%d",
        validators=[
            DataRequired(message="A data de nascimento é obrigatória."),
            validate_birth_date,
        ],
    )

    cpf = StringField(
        "CPF",
        validators=[
            Optional(),
            validate_cpf_if_organizer,
        ],
        filters=[strip_non_digits],
    )

    submit = SubmitField("Criar conta grátis")
