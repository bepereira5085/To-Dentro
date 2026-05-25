from flask_admin import Admin, AdminIndexView, expose
from flask_admin.theme import Bootstrap4Theme
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from flask import redirect, url_for, flash
from wtforms import PasswordField

from to_dentro.ext.db import db
from to_dentro.models import (
    User,
    Follow,
    Organization,
    OrganizationUser,
    Event,
    InterestedUser,
    EventOccurrence,
    EventImage,
    EventRecurrence,
    EventRecurrenceWeekday,
    Address,
    UserAddress,
    EventAddress,
    Category,
    UserCategory,
    EventCategories,
    Notification
)


class SecureAdminIndexView(AdminIndexView):
    """
    Index view (dashboard homepage) that restricts access to admin users only.
    """
    def is_accessible(self):
        from flask import current_app
        current_app.login_manager._load_user()
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)

    def inaccessible_callback(self, name, **kwargs):
        flash("Acesso não autorizado. Apenas administradores podem acessar esta área.", "danger")
        return redirect(url_for('main.login'))


class SecureModelView(ModelView):
    """
    Standard model view that restricts CRUD access to admin users only.
    """
    def is_accessible(self):
        from flask import current_app
        current_app.login_manager._load_user()
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)

    def inaccessible_callback(self, name, **kwargs):
        flash("Acesso não autorizado. Apenas administradores podem acessar esta área.", "danger")
        return redirect(url_for('main.login'))


class UserAdminView(SecureModelView):
    """
    Custom view for User model to hide raw password hashes and securely handle password resets/updates.
    """
    column_exclude_list = ('password_hash',)
    form_extra_fields = {
        'password': PasswordField('Nova Senha (deixe em branco se não quiser alterar)')
    }

    def on_model_change(self, form, model, is_created):
        if form.password.data:
            model.set_password(form.password.data)


admin = Admin(
    name='Tô Dentro! Admin',
    theme=Bootstrap4Theme(),
    index_view=SecureAdminIndexView(name='Painel Inicial')
)


def init_app(app):
    admin.init_app(app)

    # 1. Entidades Principais
    admin.add_view(UserAdminView(User, db.session, name="Usuários", category="Entidades Principais"))
    admin.add_view(SecureModelView(Organization, db.session, name="Organizações", category="Entidades Principais"))
    admin.add_view(SecureModelView(Event, db.session, name="Eventos", category="Entidades Principais"))
    admin.add_view(SecureModelView(Category, db.session, name="Categorias", category="Entidades Principais"))

    # 2. Detalhes dos Eventos
    admin.add_view(SecureModelView(EventOccurrence, db.session, name="Ocorrências", category="Detalhes dos Eventos"))
    admin.add_view(SecureModelView(EventImage, db.session, name="Imagens de Eventos", category="Detalhes dos Eventos"))
    admin.add_view(SecureModelView(EventRecurrence, db.session, name="Recorrências", category="Detalhes dos Eventos"))
    admin.add_view(SecureModelView(EventRecurrenceWeekday, db.session, name="Dias da Semana Recorrentes", category="Detalhes dos Eventos"))

    # 3. Endereços
    admin.add_view(SecureModelView(Address, db.session, name="Endereços Gerais", category="Endereços"))
    admin.add_view(SecureModelView(UserAddress, db.session, name="Endereços de Usuários", category="Endereços"))
    admin.add_view(SecureModelView(EventAddress, db.session, name="Endereços de Eventos", category="Endereços"))

    # 4. Associações / Vínculos
    admin.add_view(SecureModelView(OrganizationUser, db.session, name="Membros de Organização", category="Associações"))
    admin.add_view(SecureModelView(Follow, db.session, name="Seguidores", category="Associações"))
    admin.add_view(SecureModelView(InterestedUser, db.session, name="Usuários Interessados", category="Associações"))
    admin.add_view(SecureModelView(UserCategory, db.session, name="Categorias de Usuários", category="Associações"))
    admin.add_view(SecureModelView(EventCategories, db.session, name="Categorias de Eventos", category="Associações"))

    # 5. Sistema
    admin.add_view(SecureModelView(Notification, db.session, name="Notificações", category="Sistema"))
