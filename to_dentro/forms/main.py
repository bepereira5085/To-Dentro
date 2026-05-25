from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length

class LoginForm(FlaskForm):
    email = StringField(
        'E-mail',
        validators=[
            DataRequired(message="O campo de e-mail é obrigatório."),
            Email(message="Por favor, insira um endereço de e-mail válido.")
        ]
    )
    password = PasswordField(
        'Senha',
        validators=[
            DataRequired(message="O campo de senha é obrigatório."),
            Length(min=6, message="A senha deve conter pelo menos 6 caracteres.")
        ]
    )
    submit = SubmitField('Entrar')