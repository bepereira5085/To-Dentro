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

    admin.add_view(UserAdminView(User, db, name="Usuários", category="Entidades Principais", endpoint="admin_user"))
    admin.add_view(SecureModelView(Organization, db, name="Organizações", category="Entidades Principais"))
    admin.add_view(SecureModelView(Event, db, name="Eventos", category="Entidades Principais"))
    admin.add_view(SecureModelView(Category, db, name="Categorias", category="Entidades Principais"))

    admin.add_view(SecureModelView(EventOccurrence, db, name="Ocorrências", category="Detalhes dos Eventos"))
    admin.add_view(SecureModelView(EventImage, db, name="Imagens de Eventos", category="Detalhes dos Eventos"))
    admin.add_view(SecureModelView(EventRecurrence, db, name="Recorrências", category="Detalhes dos Eventos"))
    admin.add_view(SecureModelView(EventRecurrenceWeekday, db, name="Dias da Semana Recorrentes", category="Detalhes dos Eventos"))

    admin.add_view(SecureModelView(Address, db, name="Endereços Gerais", category="Endereços"))
    admin.add_view(SecureModelView(UserAddress, db, name="Endereços de Usuários", category="Endereços"))
    admin.add_view(SecureModelView(EventAddress, db, name="Endereços de Eventos", category="Endereços"))

    admin.add_view(SecureModelView(OrganizationUser, db, name="Membros de Organização", category="Associações"))
    admin.add_view(SecureModelView(Follow, db, name="Seguidores", category="Associações"))
    admin.add_view(SecureModelView(InterestedUser, db, name="Usuários Interessados", category="Associações"))
    admin.add_view(SecureModelView(UserCategory, db, name="Categorias de Usuários", category="Associações"))
    admin.add_view(SecureModelView(EventCategories, db, name="Categorias de Eventos", category="Associações"))

    admin.add_view(SecureModelView(Notification, db, name="Notificações", category="Sistema"))
