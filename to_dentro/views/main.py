from datetime import date, datetime, time

import requests as http_requests
from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
    abort,
    flash,
)
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.datastructures import MultiDict

from to_dentro.ext.db import db
from to_dentro.forms.main import LoginForm
from to_dentro.forms.register import RegisterForm
from to_dentro.models.address import Address
from to_dentro.models.category import Category
from to_dentro.models.event import Event
from to_dentro.models.event_address import EventAddress
from to_dentro.models.event_category import EventCategories
from to_dentro.models.event_image import EventImage
from to_dentro.models.event_occurrence import EventOccurrence
from to_dentro.models.event_recurrence import EventRecurrence, RecurrenceTypes, WeeksInterval
from to_dentro.models.event_recurrence_weekday import EventRecurrenceWeekday, WeekDays
from to_dentro.models.follows import Follow
from to_dentro.models.interested_user import InterestedUser
from to_dentro.models.notification import Notification, NotificationType
from to_dentro.models.organization import Organization
from to_dentro.models.organization_user import OrganizationUser
from to_dentro.models.user import User, UserType
from to_dentro.models.user_address import UserAddress
from to_dentro.models.user_category import UserCategory
from to_dentro.services.cep_service import (
    buscar_endereco_por_cep,
    calcular_proximidade_cep,
    obter_cep_usuario,
)
from to_dentro.services.image_service import upload_image, delete_image_by_url

main_bp = Blueprint("main", __name__)

_IBGE_BASE = "https://servicodados.ibge.gov.br/api/v1/localidades"
_IBGE_TIMEOUT = 8


def _buscar_municipios_ibge(uf: str) -> list[dict]:
    """Retorna lista de municípios do IBGE para a UF informada."""
    try:
        resp = http_requests.get(
            f"{_IBGE_BASE}/estados/{uf}/municipios?orderBy=nome",
            timeout=_IBGE_TIMEOUT,
        )
        if resp.status_code == 200:
            return [
                {"id": m["id"], "nome": m["nome"], "uf": uf.upper()}
                for m in resp.json()
            ]
    except (http_requests.RequestException, ValueError):
        pass
    return []


def _get_uf_sigla(m: dict) -> str:
    try:
        return m["microrregiao"]["mesorregiao"]["UF"]["sigla"]
    except (KeyError, TypeError):
        try:
            return m.get("regiao-imediata", {}).get("regiao-intermediaria", {}).get("UF", {}).get("sigla", "")
        except AttributeError:
            return ""

_TODOS_MUNICIPIOS_CACHE = []

def _buscar_todos_municipios_ibge() -> list[dict]:
    """Retorna lista de todos os municípios do Brasil (IBGE) com cache em memória."""
    global _TODOS_MUNICIPIOS_CACHE
    if _TODOS_MUNICIPIOS_CACHE:
        return _TODOS_MUNICIPIOS_CACHE
    try:
        resp = http_requests.get(
            f"{_IBGE_BASE}/municipios?orderBy=nome",
            timeout=_IBGE_TIMEOUT,
        )
        if resp.status_code == 200:
            _TODOS_MUNICIPIOS_CACHE = [
                {"id": m["id"], "nome": m["nome"], "uf": _get_uf_sigla(m)}
                for m in resp.json()
            ]
            return _TODOS_MUNICIPIOS_CACHE
    except (http_requests.RequestException, ValueError):
        pass
    return []


def _serializar_evento(event, occurrence, address, image_url=None, interest_count=0):
    """Serializa um evento para dicionário (uso nos templates e API JSON)."""
    categorias = []
    for ec in event.categories:
        categorias.append(ec.category.type.value)

    categoria_principal = categorias[0] if categorias else "Evento"

    data_fmt = ""
    hora_fmt = ""
    if occurrence:
        meses = [
            "", "jan.", "fev.", "mar.", "abr.", "mai.", "jun.",
            "jul.", "ago.", "set.", "out.", "nov.", "dez.",
        ]
        d = occurrence.start_date
        data_fmt = f"{d.day} de {meses[d.month]}"
        hora_fmt = occurrence.start_time.strftime("%H:%M") if occurrence.start_time else ""

    return {
        "id": event.id,
        "name": event.name,
        "description": event.description,
        "image_url": image_url or "",
        "category": categoria_principal,
        "categorias": categorias,
        "start_date": occurrence.start_date.isoformat() if occurrence else "",
        "start_date_fmt": data_fmt,
        "start_time": hora_fmt,
        "city": address.city if address else "",
        "state": address.state if address else "",
        "cep": address.cep if address else "",
        "interested_count": interest_count,
        "occurrence_id": occurrence.id if occurrence else None,
    }


def _serializar_evento_unico(event, image_url=None):
    """Serializa um evento único, buscando sua primeira ocorrência futura ou passada."""
    ocorrencia = (
        EventOccurrence.query.filter_by(event_id=event.id)
        .filter(EventOccurrence.start_date >= date.today())
        .order_by(EventOccurrence.start_date.asc())
        .first()
    )
    if not ocorrencia:
        ocorrencia = (
            EventOccurrence.query.filter_by(event_id=event.id)
            .order_by(EventOccurrence.start_date.desc())
            .first()
        )

    endereco = ocorrencia.addresses[0].address if ocorrencia and ocorrencia.addresses else None

    categorias = [ec.category.type.value for ec in event.categories]
    categoria_principal = categorias[0] if categorias else "Evento"

    data_fmt = ""
    hora_fmt = ""
    if ocorrencia:
        meses = [
            "", "jan.", "fev.", "mar.", "abr.", "mai.", "jun.",
            "jul.", "ago.", "set.", "out.", "nov.", "dez.",
        ]
        d = ocorrencia.start_date
        data_fmt = f"{d.day} de {meses[d.month]}"
        hora_fmt = ocorrencia.start_time.strftime("%H:%M") if ocorrencia.start_time else ""

    return {
        "id": event.id,
        "name": event.name,
        "description": event.description,
        "image_url": image_url or "",
        "category": categoria_principal,
        "categorias": categorias,
        "start_date": ocorrencia.start_date.isoformat() if ocorrencia else "",
        "start_date_fmt": data_fmt,
        "start_time": hora_fmt,
        "city": endereco.city if endereco else "",
        "state": endereco.state if endereco else "",
        "organization_name": event.organization.name if event.organization else "Organização",
        "organization_id": event.organization_id,
    }


def _query_eventos_com_endereco(
    q: str | None = None,
    category_ids: list[int] | None = None,
    cidade: str | None = None,
    estado: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
):
    """
    Monta a query base de eventos com JOIN em ocorrência e endereço.
    Retorna lista de tuplas (Event, EventOccurrence, Address, image_url).
    """
    query = (
        db.session.query(Event, EventOccurrence, Address)
        .join(EventOccurrence, Event.id == EventOccurrence.event_id)
        .join(EventAddress, EventOccurrence.id == EventAddress.event_occurrence_id)
        .join(Address, EventAddress.address_id == Address.id)
        .filter(EventOccurrence.start_date >= date.today())
    )

    if q:
        termo = f"%{q}%"
        query = query.filter(
            db.or_(
                Event.name.ilike(termo),
                Event.description.ilike(termo),
            )
        )

    if category_ids:
        query = query.join(
            EventCategories, Event.id == EventCategories.event_id
        ).filter(EventCategories.category_id.in_(category_ids)).distinct()

    if cidade:
        query = query.filter(Address.city.ilike(f"%{cidade}%"))

    if estado:
        query = query.filter(Address.state.ilike(f"{estado}"))

    if data_inicio:
        try:
            dt_inicio = date.fromisoformat(data_inicio)
            query = query.filter(EventOccurrence.start_date >= dt_inicio)
        except ValueError:
            pass

    if data_fim:
        try:
            dt_fim = date.fromisoformat(data_fim)
            query = query.filter(EventOccurrence.start_date <= dt_fim)
        except ValueError:
            pass

    query = query.order_by(EventOccurrence.start_date.asc())

    resultados = query.limit(200).all()

    eventos = []
    for ev, occ, addr in resultados:
        img = ev.images[0].url if ev.images else ""
        eventos.append((ev, occ, addr, img))

    return eventos


def _ordenar_por_proximidade(eventos_raw, cep_usuario: str | None):
    """
    Recebe lista de (event, occurrence, address, image_url) e ordena por
    proximidade do CEP do usuário (score decrescente → data ascendente).
    """
    if not cep_usuario:
        return eventos_raw

    def _score(item):
        _, occ, addr, _ = item
        score = calcular_proximidade_cep(cep_usuario, addr.cep or "")
        data = occ.start_date if occ else date.max
        return (-score, data)

    return sorted(eventos_raw, key=_score)




@main_bp.route("/")
def index():
    return render_template("main/index.html")


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        form = LoginForm()
        if form.validate_on_submit():
            email_digitado = form.email.data
            senha_digitada = form.password.data

            usuario = User.query.filter_by(email=email_digitado).first()

            if usuario and usuario.check_password(senha_digitada):
                login_user(usuario)
                return redirect(url_for("main.home"))
            else:
                session["login_form_data"] = request.form.to_dict()
                session["login_form_errors"] = {
                    "password": ["E-mail ou senha incorretos. Tente novamente."]
                }
                return redirect(url_for("main.login"))
        else:
            session["login_form_data"] = request.form.to_dict()
            session["login_form_errors"] = form.errors
            return redirect(url_for("main.login"))

    form_data = session.pop("login_form_data", None)
    form_errors = session.pop("login_form_errors", None)

    if form_data:
        form = LoginForm(formdata=MultiDict(form_data))
        if form_errors:
            for field_name, errors in form_errors.items():
                field = getattr(form, field_name, None)
                if field and errors:
                    field.errors = [errors[0]]
    else:
        form = LoginForm()

    return render_template("main/login.html", form=form)


@main_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        form = RegisterForm()
        if form.validate_on_submit():
            email_cleaned = form.email.data.strip().lower()
            if User.query.filter_by(email=email_cleaned).first():
                session["register_form_data"] = request.form.to_dict()
                session["register_form_errors"] = {
                    "email": [
                        "Este e-mail já está cadastrado. Tente fazer login ou informe outro e-mail."
                    ]
                }
                return redirect(url_for("main.register"))

            user_type = (
                "ORGANIZER"
                if form.user_type.data == "ORGANIZER"
                else "REGULAR"
            )
            cpf = _strip_non_digits(form.cpf.data) if user_type == "ORGANIZER" else None
            
            if user_type == "ORGANIZER" and cpf:
                if User.query.filter_by(cpf=cpf).first():
                    session["register_form_data"] = request.form.to_dict()
                    session["register_form_errors"] = {
                        "cpf": ["Este CPF já está cadastrado em outra conta."]
                    }
                    return redirect(url_for("main.register"))

            session["register_step1_data"] = {
                "name": form.name.data.strip(),
                "email": email_cleaned,
                "phone": form.phone.data,
                "birth_date": form.birth_date.data.isoformat(),
                "cep": form.cep.data,
                "cpf": cpf,
                "user_type": user_type,
                "password": form.password.data,
            }
            return redirect(url_for("main.register_step2"))
        else:
            session["register_form_data"] = request.form.to_dict()
            session["register_form_errors"] = form.errors
            return redirect(url_for("main.register"))

    form_data = session.pop("register_form_data", None)
    form_errors = session.pop("register_form_errors", None)

    if form_data:
        form = RegisterForm(formdata=MultiDict(form_data))
        if form_errors:
            for field_name, errors in form_errors.items():
                field = getattr(form, field_name, None)
                if field and errors:
                    field.errors = [errors[0]]
    else:
        step1_data = session.get("register_step1_data")
        if step1_data:
            form_dict = dict(step1_data)
            if form_dict.get("birth_date"):
                form_dict["birth_date"] = date.fromisoformat(form_dict["birth_date"])
            form = RegisterForm(formdata=MultiDict(form_dict))
        else:
            form = RegisterForm()

    return render_template("main/register.html", form=form)


@main_bp.route("/register/step2", methods=["GET", "POST"])
def register_step2():
    step1_data = session.get("register_step1_data")
    if not step1_data:
        flash("Por favor, preencha seus dados pessoais primeiro.", "is-warning")
        return redirect(url_for("main.register"))

    if request.method == "POST":
        selected_cats = request.form.getlist("categories")
        if len(selected_cats) > 10:
            flash("Você pode selecionar no máximo 10 categorias favoritas.", "is-danger")
            return redirect(url_for("main.register_step2"))

        try:
            user_type = UserType.ORGANIZER if step1_data["user_type"] == "ORGANIZER" else UserType.REGULAR
            user = User(
                name=step1_data["name"],
                email=step1_data["email"],
                phone=step1_data["phone"],
                birth_date=date.fromisoformat(step1_data["birth_date"]),
                cpf=step1_data["cpf"],
                type=user_type,
            )
            user.set_password(step1_data["password"])

            photo_file = request.files.get("photo")
            if photo_file and photo_file.filename != "":
                photo_url = upload_image(photo_file)
                if photo_url:
                    user.photo_url = photo_url

            db.session.add(user)
            db.session.flush()

            cep_value = step1_data.get("cep")
            if cep_value:
                dados_cep = buscar_endereco_por_cep(cep_value)
                address = Address(
                    street=dados_cep["logradouro"] if dados_cep else "",
                    number="",
                    city=dados_cep["cidade"] if dados_cep else "",
                    state=dados_cep["uf"] if dados_cep else "",
                    cep=cep_value,
                    country="Brasil",
                )
                db.session.add(address)
                db.session.flush()
                
                user_address = UserAddress(user_id=user.id, address_id=address.id)
                db.session.add(user_address)

            for cid in selected_cats:
                if cid.isdigit():
                    db.session.add(UserCategory(user_id=user.id, category_id=int(cid)))

            db.session.commit()
            login_user(user)
            session.pop("register_step1_data", None)
            flash("Cadastro realizado com sucesso! Seja bem-vindo ao Tô Dentro.", "is-success")
            return redirect(url_for("main.home"))

        except Exception as e:
            db.session.rollback()
            flash(f"Ocorreu um erro ao finalizar seu cadastro: {e}", "is-danger")
            return redirect(url_for("main.register_step2"))

    categories = Category.query.order_by(Category.id).all()
    name_for_initials = step1_data.get("name", "TD")
    initials = (name_for_initials[:2]).upper()

    return render_template(
        "main/register_step2.html",
        categories=categories,
        initials=initials,
    )



@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))

@main_bp.route("/home")
@login_required
def home():
    categories = Category.query.order_by(Category.id).all()

    cep_usuario = obter_cep_usuario(current_user)
    cidade_usuario = ""
    uf_usuario = ""
    if cep_usuario:
        dados = buscar_endereco_por_cep(cep_usuario)
        if dados:
            cidade_usuario = dados.get("cidade", "")
            uf_usuario = dados.get("uf", "")

    if not cidade_usuario and current_user.addresses:
        addr = current_user.addresses[0].address
        if addr:
            cidade_usuario = addr.city or ""
            uf_usuario = addr.state or ""

    municipios = _buscar_todos_municipios_ibge()

    todos_eventos = _query_eventos_com_endereco()
    eventos_proximos_raw = _ordenar_por_proximidade(todos_eventos, cep_usuario)
    eventos_proximos_total = len(eventos_proximos_raw)
    eventos_proximos = [
        _serializar_evento(ev, occ, addr, img)
        for ev, occ, addr, img in eventos_proximos_raw
    ]

    eventos_galera = []
    if current_user.following:
        followed_ids = [f.following_id for f in current_user.following]

        galera_raw_query = (
            db.session.query(Event, EventOccurrence, Address)
            .join(InterestedUser, Event.id == InterestedUser.event_id)
            .join(EventOccurrence, Event.id == EventOccurrence.event_id)
            .join(EventAddress, EventOccurrence.id == EventAddress.event_occurrence_id)
            .join(Address, EventAddress.address_id == Address.id)
            .filter(InterestedUser.user_id.in_(followed_ids))
            .filter(EventOccurrence.start_date >= date.today())
            .order_by(EventOccurrence.start_date.asc())
            .limit(200)
            .all()
        )

        galera_raw = []
        seen_event_ids = set()
        for ev, occ, addr in galera_raw_query:
            if ev.id not in seen_event_ids:
                img = ev.images[0].url if ev.images else ""
                galera_raw.append((ev, occ, addr, img))
                seen_event_ids.add(ev.id)

        galera_sorted = _ordenar_por_proximidade(galera_raw, cep_usuario)
        eventos_galera = [
            _serializar_evento(ev, occ, addr, img)
            for ev, occ, addr, img in galera_sorted
        ]

    return render_template(
        "main/home.html",
        categories=categories,
        eventos_proximos=eventos_proximos,
        eventos_proximos_total=eventos_proximos_total,
        eventos_galera=eventos_galera,
        cidade_usuario=cidade_usuario,
        uf_usuario=uf_usuario,
        cep_usuario=cep_usuario,
        municipios=municipios,
        page_size=15,
    )

@main_bp.route("/evento/<int:event_id>")
@login_required
def event_details(event_id):
    event = Event.query.get_or_404(event_id)

    ocorrencia = (
        EventOccurrence.query.filter_by(event_id=event.id)
        .filter(EventOccurrence.start_date >= date.today())
        .order_by(EventOccurrence.start_date.asc())
        .first()
    )
    if not ocorrencia:
        ocorrencia = (
            EventOccurrence.query.filter_by(event_id=event.id)
            .order_by(EventOccurrence.start_date.desc())
            .first()
        )

    endereco = None
    if ocorrencia and ocorrencia.addresses:
        endereco = ocorrencia.addresses[0].address

    imagem_url = event.images[0].url if event.images else ""

    categorias = [ec.category.type.value for ec in event.categories]

    usuario_interessado = (
        InterestedUser.query.filter_by(
            user_id=current_user.id, event_id=event.id
        ).first()
        is not None
    )

    meses = [
        "", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    ]
    data_fmt = ""
    hora_fmt = ""
    if ocorrencia:
        d = ocorrencia.start_date
        data_fmt = f"{d.day} de {meses[d.month]} de {d.year}"
        hora_fmt = (
            ocorrencia.start_time.strftime("%H:%M") if ocorrencia.start_time else ""
        )

    organizador_dono = False
    if current_user.is_authenticated and current_user.type == UserType.ORGANIZER:
        organizador_dono = event.organization_id in [ou.organization_id for ou in current_user.organizations]

    return render_template(
        "main/event_details.html",
        event=event,
        ocorrencia=ocorrencia,
        endereco=endereco,
        imagem_url=imagem_url,
        categorias=categorias,
        data_fmt=data_fmt,
        hora_fmt=hora_fmt,
        usuario_interessado=usuario_interessado,
        organizador_dono=organizador_dono,
    )

@main_bp.route("/api/cep/<cep>")
def api_buscar_cep(cep):
    dados = buscar_endereco_por_cep(cep)
    if not dados:
        return jsonify({"error": "CEP não encontrado"}), 404
    return jsonify(dados)

@main_bp.route("/api/ibge/municipios")
def api_ibge_municipios():
    """Retorna municípios filtrados por UF (query param ?uf=ES)."""
    uf = request.args.get("uf", "").strip().upper()
    if not uf:
        return jsonify({"error": "Parâmetro 'uf' é obrigatório"}), 400

    municipios = _buscar_municipios_ibge(uf)
    return jsonify(municipios)

@main_bp.route("/api/eventos/buscar")
@login_required
def api_buscar_eventos():
    q = request.args.get("q", "").strip() or None
    category_ids_str = request.args.get("categorias", "").strip()
    cidade = request.args.get("cidade", "").strip() or None
    estado = request.args.get("estado", "").strip() or None
    data_inicio = request.args.get("data_inicio", "").strip() or None
    data_fim = request.args.get("data_fim", "").strip() or None
    page = int(request.args.get("page", 1))
    page_size = 15

    category_ids = []
    if category_ids_str:
        for cid in category_ids_str.split(","):
            if cid.strip().isdigit():
                category_ids.append(int(cid.strip()))
    else:
        legacy_cat = request.args.get("categoria", "").strip()
        if legacy_cat and legacy_cat.isdigit():
            category_ids.append(int(legacy_cat))

    eventos_raw = _query_eventos_com_endereco(
        q=q,
        category_ids=category_ids or None,
        cidade=cidade,
        estado=estado,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    cep_usuario = obter_cep_usuario(current_user)
    eventos_sorted = _ordenar_por_proximidade(eventos_raw, cep_usuario)

    total = len(eventos_sorted)
    inicio = (page - 1) * page_size
    fim = inicio + page_size
    pagina = eventos_sorted[inicio:fim]

    eventos_json = [
        _serializar_evento(ev, occ, addr, img) for ev, occ, addr, img in pagina
    ]

    return jsonify(
        {
            "eventos": eventos_json,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": fim < total,
            "has_prev": page > 1,
        }
    )

def _calcular_idade(birth_date):
    """Calcula a idade em anos a partir da data de nascimento."""
    hoje = date.today()
    return (
        hoje.year - birth_date.year
        - ((hoje.month, hoje.day) < (birth_date.month, birth_date.day))
    )


def _serializar_usuario(user, current_user_category_ids=None):
    """Serializa um usuário para dicionário."""
    primeiro_nome = user.name.split()[0] if user.name else ""
    idade = _calcular_idade(user.birth_date) if user.birth_date else None

    categorias = []
    for uc in user.categories:
        is_common = (
            uc.category_id in current_user_category_ids
            if current_user_category_ids is not None
            else False
        )
        categorias.append({
            "id": uc.category_id,
            "name": uc.category.type.value,
            "is_common": is_common,
        })

    return {
        "id": user.id,
        "name": user.name,
        "first_name": primeiro_nome,
        "age": idade,
        "photo_url": user.photo_url,
        "categories": categorias,
        "initials": (user.name[:2]).upper() if user.name else "??",
    }


def _ultimos_eventos_usuario(user_id, limit=5):
    """Retorna os últimos eventos que o usuário marcou Tô Dentro!"""
    resultados = (
        db.session.query(Event, EventOccurrence, Address)
        .join(InterestedUser, Event.id == InterestedUser.event_id)
        .join(EventOccurrence, Event.id == EventOccurrence.event_id)
        .join(EventAddress, EventOccurrence.id == EventAddress.event_occurrence_id)
        .join(Address, EventAddress.address_id == Address.id)
        .filter(InterestedUser.user_id == user_id)
        .order_by(InterestedUser.created_at.desc())
        .limit(limit)
        .all()
    )

    meses = ["", "jan.", "fev.", "mar.", "abr.", "mai.", "jun.",
             "jul.", "ago.", "set.", "out.", "nov.", "dez."]

    eventos = []
    for ev, occ, addr in resultados:
        img = ev.images[0].url if ev.images else ""
        d = occ.start_date
        data_fmt = f"{d.day} de {meses[d.month]}" if occ else ""
        hora_fmt = occ.start_time.strftime("%H:%M") if occ and occ.start_time else ""
        categorias = [ec.category.type.value for ec in ev.categories]
        eventos.append({
            "id": ev.id,
            "name": ev.name,
            "image_url": img,
            "category": categorias[0] if categorias else "Evento",
            "start_date_fmt": data_fmt,
            "start_time": hora_fmt,
            "city": addr.city if addr else "",
            "state": addr.state if addr else "",
        })
    return eventos

@main_bp.route("/amigos")
@login_required
def friends():
    """Página principal de amigos — lista os usuários que o logado segue."""
    seguindo = (
        db.session.query(User)
        .join(Follow, Follow.following_id == User.id)
        .filter(Follow.follower_id == current_user.id)
        .order_by(User.name.asc())
        .all()
    )
    return render_template("main/friends.html", seguindo=seguindo)


@main_bp.route("/api/usuario/<int:user_id>/detalhes")
@login_required
def api_usuario_detalhes(user_id):
    """Retorna JSON com todos os detalhes de um usuário para o modal flutuante."""
    usuario = User.query.get_or_404(user_id)

    my_category_ids = {uc.category_id for uc in current_user.categories}

    categorias = [
        {
            "name": uc.category.type.value,
            "is_common": uc.category_id in my_category_ids,
        }
        for uc in usuario.categories
    ]

    ultimos_eventos = _ultimos_eventos_usuario(user_id, limit=5)

    is_following = Follow.query.filter_by(
        follower_id=current_user.id,
        following_id=user_id,
    ).first() is not None

    primeiro_nome = usuario.name.split()[0] if usuario.name else ""
    idade = _calcular_idade(usuario.birth_date) if usuario.birth_date else None

    return jsonify({
        "id": usuario.id,
        "name": usuario.name,
        "first_name": primeiro_nome,
        "age": idade,
        "photo_url": usuario.photo_url,
        "initials": (usuario.name[:2]).upper() if usuario.name else "??",
        "categories": categorias,
        "recent_events": ultimos_eventos,
        "is_following": is_following,
    })



@main_bp.route("/usuario/<int:user_id>")
@login_required
def user_details(user_id):
    """Página de detalhes de um usuário — renderizada via Jinja2."""
    usuario = User.query.get_or_404(user_id)

    my_category_ids = {uc.category_id for uc in current_user.categories}

    categorias = []
    for uc in usuario.categories:
        categorias.append({
            "name": uc.category.type.value,
            "is_common": uc.category_id in my_category_ids,
        })

    ultimos_eventos = _ultimos_eventos_usuario(user_id, limit=5)

    is_following = Follow.query.filter_by(
        follower_id=current_user.id,
        following_id=user_id,
    ).first() is not None

    primeiro_nome = usuario.name.split()[0] if usuario.name else ""
    idade = _calcular_idade(usuario.birth_date) if usuario.birth_date else None

    return render_template(
        "main/user_details.html",
        usuario=usuario,
        primeiro_nome=primeiro_nome,
        idade=idade,
        categorias=categorias,
        ultimos_eventos=ultimos_eventos,
        is_following=is_following,
    )


@main_bp.route("/api/amigos/buscar")
@login_required
def api_buscar_amigos():
    """Busca entre os usuários que o logado já segue."""
    q = request.args.get("q", "").strip()

    query = (
        db.session.query(User)
        .join(Follow, Follow.following_id == User.id)
        .filter(Follow.follower_id == current_user.id)
    )
    if q:
        query = query.filter(User.name.ilike(f"%{q}%"))

    usuarios = query.order_by(User.name.asc()).limit(50).all()

    return jsonify([
        {
            "id": u.id,
            "name": u.name,
            "first_name": u.name.split()[0],
            "initials": (u.name[:2]).upper(),
            "photo_url": u.photo_url,
            "age": _calcular_idade(u.birth_date) if u.birth_date else None,
        }
        for u in usuarios
    ])


@main_bp.route("/api/usuarios/buscar")
@login_required
def api_buscar_usuarios():
    """Busca usuários que o logado ainda não segue (para 'Encontrar amigos')."""
    q = request.args.get("q", "").strip()

    seguindo_ids = [f.following_id for f in current_user.following]
    seguindo_ids.append(current_user.id)

    query = User.query.filter(User.id.notin_(seguindo_ids))
    if q:
        query = query.filter(User.name.ilike(f"%{q}%"))

    usuarios = query.order_by(User.name.asc()).limit(30).all()

    return jsonify([
        {
            "id": u.id,
            "name": u.name,
            "first_name": u.name.split()[0],
            "initials": (u.name[:2]).upper(),
            "photo_url": u.photo_url,
            "age": _calcular_idade(u.birth_date) if u.birth_date else None,
        }
        for u in usuarios
    ])


@main_bp.route("/api/follow/<int:user_id>", methods=["POST"])
@login_required
def api_follow(user_id):
    """Seguir um usuário e criar notificação do tipo FOLLOW."""
    if user_id == current_user.id:
        return jsonify({"error": "Você não pode seguir a si mesmo."}), 400

    target = User.query.get_or_404(user_id)

    ja_segue = Follow.query.filter_by(
        follower_id=current_user.id,
        following_id=user_id,
    ).first()

    if ja_segue:
        return jsonify({"status": "already_following"}), 200

    follow = Follow(follower_id=current_user.id, following_id=user_id)
    db.session.add(follow)

    notificacao = Notification(
        actor_user_id=current_user.id,
        recipient_user_id=user_id,
        type=NotificationType.FOLLOW,
    )
    db.session.add(notificacao)

    db.session.commit()
    return jsonify({"status": "following"}), 200


@main_bp.route("/api/unfollow/<int:user_id>", methods=["POST"])
@login_required
def api_unfollow(user_id):
    """Deixar de seguir um usuário."""
    follow = Follow.query.filter_by(
        follower_id=current_user.id,
        following_id=user_id,
    ).first()

    if not follow:
        return jsonify({"status": "not_following"}), 200

    db.session.delete(follow)
    db.session.commit()
    return jsonify({"status": "unfollowed"}), 200


@main_bp.route("/api/evento/<int:event_id>/toggle-interest", methods=["POST"])
@login_required
def api_toggle_interest(event_id):
    event = Event.query.get_or_404(event_id)

    ocorrencia = (
        EventOccurrence.query.filter_by(event_id=event.id)
        .filter(EventOccurrence.start_date >= date.today())
        .order_by(EventOccurrence.start_date.asc())
        .first()
    )
    if not ocorrencia:
        ocorrencia = (
            EventOccurrence.query.filter_by(event_id=event.id)
            .order_by(EventOccurrence.start_date.desc())
            .first()
        )

    interest = InterestedUser.query.filter_by(
        user_id=current_user.id, event_id=event.id
    ).first()

    if interest:
        db.session.delete(interest)
        if ocorrencia:
            ocorrencia.interested_count = max(0, ocorrencia.interested_count - 1)

            Notification.query.filter_by(
                actor_user_id=current_user.id,
                event_occurrence_id=ocorrencia.id,
                type=NotificationType.FRIEND_JOINED_EVENT,
            ).delete()

        db.session.commit()
        return jsonify({
            "status": "removed",
            "interested_count": ocorrencia.interested_count if ocorrencia else 0
        }), 200
    else:
        interest = InterestedUser(user_id=current_user.id, event_id=event.id)
        db.session.add(interest)
        if ocorrencia:
            ocorrencia.interested_count += 1

            event_cat_ids = {ec.category_id for ec in event.categories}

            for follow_obj in current_user.followers:
                follower = follow_obj.follower
                recipient_fav_cat_ids = {uc.category_id for uc in follower.categories}

                if event_cat_ids.intersection(recipient_fav_cat_ids):
                    notificacao = Notification(
                        actor_user_id=current_user.id,
                        recipient_user_id=follower.id,
                        event_occurrence_id=ocorrencia.id,
                        type=NotificationType.FRIEND_JOINED_EVENT,
                    )
                    db.session.add(notificacao)

        db.session.commit()
        return jsonify({
            "status": "added",
            "interested_count": ocorrencia.interested_count if ocorrencia else 0
        }), 200


@main_bp.route("/api/notificacoes")
@login_required
def api_notificacoes():
    """Retorna as notificações não lidas do usuário logado."""
    _event_notif_types = [
        NotificationType.EVENT_INTERESTED,
        NotificationType.FRIEND_JOINED_EVENT,
    ]

    notificacoes = (
        Notification.query
        .filter_by(recipient_user_id=current_user.id, is_read=False)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )

    resultado = []
    for n in notificacoes:
        actor_name = n.actor.name if n.actor else "Alguém"
        evento_nome = None
        evento_id = None

        if n.type == NotificationType.FOLLOW:
            mensagem = f"{actor_name} falou que você tá sempre junto no rolê!"
        elif n.type in _event_notif_types:
            if n.event_occurrence and n.event_occurrence.event:
                evento_nome = n.event_occurrence.event.name
                evento_id = n.event_occurrence.event.id
            mensagem = f"{actor_name} tá dentro desse rolê: {evento_nome or 'Evento desconhecido'}"
        else:
            continue

        resultado.append({
            "id": n.id,
            "tipo": n.type.value,
            "mensagem": mensagem,
            "evento_nome": evento_nome,
            "evento_id": evento_id,
            "actor_id": n.actor_user_id,
            "actor_name": actor_name,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        })

    return jsonify({"notificacoes": resultado, "total": len(resultado)})


@main_bp.route("/api/notificacoes/<int:notif_id>/marcar-lida", methods=["POST"])
@login_required
def api_marcar_notificacao_lida(notif_id):
    """Marca uma notificação como lida (apenas se pertencer ao usuário logado)."""
    notif = Notification.query.get_or_404(notif_id)

    if notif.recipient_user_id != current_user.id:
        return jsonify({"error": "Sem permissão."}), 403

    notif.is_read = True
    db.session.commit()
    return jsonify({"status": "ok"}), 200


@main_bp.route("/meus-eventos")
@login_required
def my_events():
    if current_user.type != UserType.ORGANIZER:
        abort(403)

    orgs = [ou.organization for ou in current_user.organizations]
    categories = Category.query.order_by(Category.id).all()
    municipios = _buscar_todos_municipios_ibge()

    return render_template(
        "main/my_events.html",
        organizations=orgs,
        categories=categories,
        municipios=municipios,
    )


@main_bp.route("/api/meus-eventos/buscar")
@login_required
def api_buscar_meus_eventos():
    if current_user.type != UserType.ORGANIZER:
        return jsonify({"error": "Acesso não autorizado."}), 403

    org_ids = [ou.organization_id for ou in current_user.organizations]
    if not org_ids:
        return jsonify({"eventos": [], "total": 0})

    q = request.args.get("q", "").strip() or None
    category_ids_str = request.args.get("categorias", "").strip()
    cidade = request.args.get("cidade", "").strip() or None
    estado = request.args.get("estado", "").strip() or None
    data_inicio = request.args.get("data_inicio", "").strip() or None
    data_fim = request.args.get("data_fim", "").strip() or None
    org_id = request.args.get("organizacao_id", "").strip() or None
    page = int(request.args.get("page", 1))
    page_size = 15

    query = Event.query.filter(Event.organization_id.in_(org_ids))

    if org_id and org_id.isdigit():
        query = query.filter(Event.organization_id == int(org_id))

    if q:
        termo = f"%{q}%"
        query = query.filter(
            db.or_(
                Event.name.ilike(termo),
                Event.description.ilike(termo),
            )
        )

    if category_ids_str:
        cids = [int(x) for x in category_ids_str.split(",") if x.strip().isdigit()]
        if cids:
            query = query.join(EventCategories).filter(
                EventCategories.category_id.in_(cids)
            )

    if cidade or estado or data_inicio or data_fim:
        query = query.join(EventOccurrence).join(EventAddress).join(Address)
        if cidade:
            query = query.filter(Address.city.ilike(f"%{cidade}%"))
        if estado:
            query = query.filter(Address.state.ilike(f"{estado}"))
        if data_inicio:
            try:
                dt_inicio = date.fromisoformat(data_inicio)
                query = query.filter(EventOccurrence.start_date >= dt_inicio)
            except ValueError:
                pass
        if data_fim:
            try:
                dt_fim = date.fromisoformat(data_fim)
                query = query.filter(EventOccurrence.start_date <= dt_fim)
            except ValueError:
                pass

    query = query.distinct()
    total = query.count()
    eventos_pagina = (
        query.order_by(Event.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    eventos_json = []
    for ev in eventos_pagina:
        img_url = ev.images[0].url if ev.images else ""
        eventos_json.append(_serializar_evento_unico(ev, image_url=img_url))

    return jsonify(
        {
            "eventos": eventos_json,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": (page * page_size) < total,
            "has_prev": page > 1,
        }
    )


@main_bp.route("/criar-evento", methods=["GET", "POST"])
@login_required
def create_event():
    if current_user.type != UserType.ORGANIZER:
        abort(403)

    orgs = [ou.organization for ou in current_user.organizations]
    if not orgs:
        flash(
            "Você precisa estar associado a pelo menos uma organização para criar eventos.",
            "is-warning",
        )
        return redirect(url_for("main.home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        org_id = request.form.get("organization_id")
        is_recurrent = request.form.get("is_recurrent") in ("true", "on", "1")

        cat_ids = request.form.getlist("categories")

        cep = request.form.get("cep", "").strip().replace("-", "")
        street = request.form.get("street", "").strip()
        number = request.form.get("number", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        country = request.form.get("country", "Brasil").strip()

        start_date_str = request.form.get("start_date")
        start_time_str = request.form.get("start_time")
        duration_days_str = request.form.get("duration_days", "1")
        duration_time_str = request.form.get("duration_time")
        observations = request.form.get("observations", "").strip() or None

        rec_type_str = request.form.get("recurrence_type")
        rec_end_date_str = request.form.get("end_date")
        rec_weeks_str = request.form.get("weeks_interval")
        rec_day_month_str = request.form.get("day_of_month")
        rec_weekdays = request.form.getlist("weekdays")

        try:
            if not org_id or int(org_id) not in [o.id for o in orgs]:
                raise ValueError("Organização inválida ou não pertence a você.")

            if not name:
                raise ValueError("O nome do evento é obrigatório.")

            if not start_date_str or not start_time_str:
                raise ValueError("Data e hora de início são obrigatórias.")

            start_date_val = date.fromisoformat(start_date_str)
            start_time_val = time.fromisoformat(start_time_str)

            duration_days_val = (
                int(duration_days_str) if duration_days_str.isdigit() else 1
            )
            if duration_days_val < 1:
                duration_days_val = 1

            duration_time_val = None
            if duration_time_str:
                try:
                    duration_time_val = time.fromisoformat(duration_time_str)
                except ValueError:
                    pass

            address = Address(
                street=street,
                number=number,
                city=city,
                state=state,
                cep=cep,
                country=country,
            )
            db.session.add(address)
            db.session.flush()

            event = Event(
                organization_id=int(org_id),
                name=name,
                description=description,
                is_recurrent=is_recurrent,
            )
            db.session.add(event)
            db.session.flush()

            dates_to_create = [start_date_val]

            if is_recurrent:
                if not rec_type_str:
                    raise ValueError(
                        "Tipo de recorrência é obrigatório para eventos recorrentes."
                    )

                end_date_val = None
                if rec_end_date_str:
                    try:
                        end_date_val = date.fromisoformat(rec_end_date_str)
                    except ValueError:
                        pass

                weeks_interval_val = None
                if rec_weeks_str and rec_weeks_str in ("ONE", "TWO"):
                    weeks_interval_val = WeeksInterval[rec_weeks_str]

                day_of_month_val = None
                if rec_day_month_str and rec_day_month_str.isdigit():
                    day_of_month_val = int(rec_day_month_str)
                    if not (1 <= day_of_month_val <= 31):
                        day_of_month_val = None

                rec_type_val = (
                    RecurrenceTypes[rec_type_str]
                    if rec_type_str in RecurrenceTypes.__members__
                    else RecurrenceTypes.DAILY
                )

                recurrence = EventRecurrence(
                    event_id=event.id,
                    type=rec_type_val,
                    start_date=start_date_val,
                    end_date=end_date_val,
                    weeks_interval=weeks_interval_val,
                    day_of_month=day_of_month_val,
                )
                db.session.add(recurrence)
                db.session.flush()

                weekdays_enum_list = []
                for wday in rec_weekdays:
                    if wday in WeekDays.__members__:
                        db.session.add(
                            EventRecurrenceWeekday(
                                recurrence_id=recurrence.id,
                                weekday=WeekDays[wday],
                            )
                        )
                        weekdays_enum_list.append(WeekDays[wday])

                from to_dentro.utils.recurrence import generate_recurrence_dates
                dates_to_create = generate_recurrence_dates(
                    start_date=start_date_val,
                    end_date=end_date_val,
                    rec_type=rec_type_val,
                    weeks_interval=weeks_interval_val,
                    day_of_month=day_of_month_val,
                    weekdays=weekdays_enum_list
                )

            for dt in dates_to_create:
                occurrence = EventOccurrence(
                    event_id=event.id,
                    observations=observations,
                    interested_count=0,
                    start_date=dt,
                    duration_days=duration_days_val,
                    start_time=start_time_val,
                    duration_time=duration_time_val,
                )
                db.session.add(occurrence)
                db.session.flush()

                event_address = EventAddress(
                    event_occurrence_id=occurrence.id, address_id=address.id
                )
                db.session.add(event_address)

            for cid in cat_ids:
                if cid.isdigit():
                    db.session.add(
                        EventCategories(event_id=event.id, category_id=int(cid))
                    )

            files = request.files.getlist("images")
            uploaded_count = 0
            for file in files:
                if file and file.filename != "":
                    if uploaded_count >= 5:
                        break
                    url = upload_image(file)
                    if url:
                        db.session.add(EventImage(event_id=event.id, url=url))
                        uploaded_count += 1

            db.session.commit()
            flash("Evento criado com sucesso!", "is-success")
            return redirect(url_for("main.my_events"))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao criar evento: {e}", "is-danger")

    categories = Category.query.order_by(Category.id).all()
    return render_template(
        "main/create_event.html", organizations=orgs, categories=categories
    )


@main_bp.route("/evento/<int:event_id>/editar", methods=["GET", "POST"])
@login_required
def edit_event(event_id):
    if current_user.type != UserType.ORGANIZER:
        abort(403)

    event = Event.query.get_or_404(event_id)

    orgs = [ou.organization for ou in current_user.organizations]
    if event.organization_id not in [o.id for o in orgs]:
        abort(403)

    occurrence = (
        EventOccurrence.query.filter_by(event_id=event.id)
        .filter(EventOccurrence.start_date >= date.today())
        .order_by(EventOccurrence.start_date.asc())
        .first()
    )
    if not occurrence:
        occurrence = (
            EventOccurrence.query.filter_by(event_id=event.id)
            .order_by(EventOccurrence.start_date.desc())
            .first()
        )

    address = occurrence.addresses[0].address if occurrence and occurrence.addresses else None
    recurrence = EventRecurrence.query.filter_by(event_id=event.id).first()
    recurrence_weekdays = [rw.weekday.name for rw in recurrence.weekdays] if recurrence else []
    selected_category_ids = [ec.category_id for ec in event.categories]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        org_id = request.form.get("organization_id")
        is_recurrent = request.form.get("is_recurrent") in ("true", "on", "1")

        cat_ids = request.form.getlist("categories")

        cep = request.form.get("cep", "").strip().replace("-", "")
        street = request.form.get("street", "").strip()
        number = request.form.get("number", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        country = request.form.get("country", "Brasil").strip()

        start_date_str = request.form.get("start_date")
        start_time_str = request.form.get("start_time")
        duration_days_str = request.form.get("duration_days", "1")
        duration_time_str = request.form.get("duration_time")
        observations = request.form.get("observations", "").strip() or None

        rec_type_str = request.form.get("recurrence_type")
        rec_end_date_str = request.form.get("end_date")
        rec_weeks_str = request.form.get("weeks_interval")
        rec_day_month_str = request.form.get("day_of_month")
        rec_weekdays = request.form.getlist("weekdays")

        deleted_image_ids = request.form.getlist("deleted_images")

        try:
            if not org_id or int(org_id) not in [o.id for o in orgs]:
                raise ValueError("Organização inválida ou não pertence a você.")

            if not name:
                raise ValueError("O nome do evento é obrigatório.")

            if not start_date_str or not start_time_str:
                raise ValueError("Data e hora de início são obrigatórias.")

            start_date_val = date.fromisoformat(start_date_str)
            start_time_val = time.fromisoformat(start_time_str)

            duration_days_val = (
                int(duration_days_str) if duration_days_str.isdigit() else 1
            )
            if duration_days_val < 1:
                duration_days_val = 1

            duration_time_val = None
            if duration_time_str:
                try:
                    duration_time_val = time.fromisoformat(duration_time_str)
                except ValueError:
                    pass

            remaining_existing = len(event.images) - len(deleted_image_ids)
            new_files = request.files.getlist("images")
            valid_new_files = [f for f in new_files if f and f.filename != ""]

            if remaining_existing + len(valid_new_files) > 5:
                raise ValueError("O evento pode ter no máximo 5 imagens no total.")

            for img_id_str in deleted_image_ids:
                if img_id_str.isdigit():
                    img = EventImage.query.get(int(img_id_str))
                    if img and img.event_id == event.id:
                        if img.url:
                            delete_image_by_url(img.url)
                        db.session.delete(img)

            for file in valid_new_files:
                url = upload_image(file)
                if url:
                    db.session.add(EventImage(event_id=event.id, url=url))

            if address:
                address.cep = cep
                address.street = street
                address.number = number
                address.city = city
                address.state = state
                address.country = country
            else:
                address = Address(
                    street=street,
                    number=number,
                    city=city,
                    state=state,
                    cep=cep,
                    country=country,
                )
                db.session.add(address)
                db.session.flush()

            date_or_recurrence_changed = False

            old_is_recurrent = event.is_recurrent
            old_start_date = None
            old_rec_type = None
            old_end_date = None
            old_weeks_interval = None
            old_day_of_month = None
            old_weekdays = set()

            if recurrence:
                old_start_date = recurrence.start_date
                old_rec_type = recurrence.type
                old_end_date = recurrence.end_date
                old_weeks_interval = recurrence.weeks_interval
                old_day_of_month = recurrence.day_of_month
                old_weekdays = {rw.weekday.name for rw in recurrence.weekdays}

            new_end_date_val = None
            if rec_end_date_str:
                try:
                    new_end_date_val = date.fromisoformat(rec_end_date_str)
                except ValueError:
                    pass

            new_weeks_interval_val = None
            if rec_weeks_str and rec_weeks_str in ("ONE", "TWO"):
                new_weeks_interval_val = WeeksInterval[rec_weeks_str]

            new_day_of_month_val = None
            if rec_day_month_str and rec_day_month_str.isdigit():
                new_day_of_month_val = int(rec_day_month_str)
                if not (1 <= new_day_of_month_val <= 31):
                    new_day_of_month_val = None

            new_rec_type_val = None
            if rec_type_str in RecurrenceTypes.__members__:
                new_rec_type_val = RecurrenceTypes[rec_type_str]

            new_weekdays_set = set(rec_weekdays)

            if old_is_recurrent != is_recurrent:
                date_or_recurrence_changed = True
            elif is_recurrent:
                if old_start_date != start_date_val:
                    date_or_recurrence_changed = True
                elif old_rec_type != new_rec_type_val:
                    date_or_recurrence_changed = True
                elif old_end_date != new_end_date_val:
                    date_or_recurrence_changed = True
                elif old_weeks_interval != new_weeks_interval_val:
                    date_or_recurrence_changed = True
                elif old_day_of_month != new_day_of_month_val:
                    date_or_recurrence_changed = True
                elif old_weekdays != new_weekdays_set:
                    date_or_recurrence_changed = True

            event.organization_id = int(org_id)
            event.name = name
            event.description = description
            event.is_recurrent = is_recurrent

            today = date.today()
            from datetime import timedelta

            if date_or_recurrence_changed:
                future_occurrences = EventOccurrence.query.filter_by(event_id=event.id).filter(EventOccurrence.start_date > today).all()
                for f_occ in future_occurrences:
                    EventAddress.query.filter_by(event_occurrence_id=f_occ.id).delete()
                    db.session.delete(f_occ)
                db.session.flush()

                new_dates = []
                if is_recurrent:
                    tomorrow = today + timedelta(days=1)
                    gen_start_date = max(start_date_val, tomorrow)

                    weekdays_enum_list = []

                    if recurrence:
                        EventRecurrenceWeekday.query.filter_by(recurrence_id=recurrence.id).delete()
                        db.session.delete(recurrence)
                        db.session.flush()

                    new_recurrence = EventRecurrence(
                        event_id=event.id,
                        type=new_rec_type_val,
                        start_date=start_date_val,
                        end_date=new_end_date_val,
                        weeks_interval=new_weeks_interval_val,
                        day_of_month=new_day_of_month_val,
                    )
                    db.session.add(new_recurrence)
                    db.session.flush()

                    for wday in rec_weekdays:
                        if wday in WeekDays.__members__:
                            db.session.add(
                                EventRecurrenceWeekday(
                                    recurrence_id=new_recurrence.id,
                                    weekday=WeekDays[wday],
                                )
                            )
                            weekdays_enum_list.append(WeekDays[wday])

                    from to_dentro.utils.recurrence import generate_recurrence_dates
                    new_dates = generate_recurrence_dates(
                        start_date=gen_start_date,
                        end_date=new_end_date_val,
                        rec_type=new_rec_type_val,
                        weeks_interval=new_weeks_interval_val,
                        day_of_month=new_day_of_month_val,
                        weekdays=weekdays_enum_list
                    )
                else:
                    if recurrence:
                        EventRecurrenceWeekday.query.filter_by(recurrence_id=recurrence.id).delete()
                        db.session.delete(recurrence)
                        db.session.flush()

                    if start_date_val > today:
                        new_dates = [start_date_val]

                for dt in new_dates:
                    new_occ = EventOccurrence(
                        event_id=event.id,
                        observations=observations,
                        interested_count=0,
                        start_date=dt,
                        duration_days=duration_days_val,
                        start_time=start_time_val,
                        duration_time=duration_time_val,
                    )
                    db.session.add(new_occ)
                    db.session.flush()

                    db.session.add(
                        EventAddress(
                            event_occurrence_id=new_occ.id, address_id=address.id
                        )
                    )

                if occurrence and occurrence.start_date <= today:
                    occurrence.observations = observations
                    occurrence.duration_days = duration_days_val
                    occurrence.start_time = start_time_val
                    occurrence.duration_time = duration_time_val

                    has_assoc = False
                    if occurrence.addresses:
                        for ea in occurrence.addresses:
                            if ea.address_id == address.id:
                                has_assoc = True
                    if not has_assoc:
                        db.session.add(
                            EventAddress(
                                event_occurrence_id=occurrence.id, address_id=address.id
                            )
                        )
            else:
                if is_recurrent and recurrence:
                    pass
                elif is_recurrent and not recurrence:
                    new_recurrence = EventRecurrence(
                        event_id=event.id,
                        type=new_rec_type_val,
                        start_date=start_date_val,
                        end_date=new_end_date_val,
                        weeks_interval=new_weeks_interval_val,
                        day_of_month=new_day_of_month_val,
                    )
                    db.session.add(new_recurrence)
                    db.session.flush()
                    for wday in rec_weekdays:
                        if wday in WeekDays.__members__:
                            db.session.add(
                                EventRecurrenceWeekday(
                                    recurrence_id=new_recurrence.id,
                                    weekday=WeekDays[wday],
                                )
                            )

                future_occurrences = EventOccurrence.query.filter_by(event_id=event.id).filter(EventOccurrence.start_date > today).all()
                for f_occ in future_occurrences:
                    f_occ.observations = observations
                    f_occ.duration_days = duration_days_val
                    f_occ.start_time = start_time_val
                    f_occ.duration_time = duration_time_val

                if occurrence and occurrence.start_date <= today:
                    occurrence.observations = observations
                    occurrence.duration_days = duration_days_val
                    occurrence.start_time = start_time_val
                    occurrence.duration_time = duration_time_val

                    has_assoc = False
                    if occurrence.addresses:
                        for ea in occurrence.addresses:
                            if ea.address_id == address.id:
                                has_assoc = True
                    if not has_assoc:
                        db.session.add(
                            EventAddress(
                                event_occurrence_id=occurrence.id, address_id=address.id
                            )
                        )

            EventCategories.query.filter_by(event_id=event.id).delete()
            for cid in cat_ids:
                if cid.isdigit():
                    db.session.add(
                        EventCategories(event_id=event.id, category_id=int(cid))
                    )

            db.session.commit()
            flash("Evento atualizado com sucesso!", "is-success")
            return redirect(url_for("main.my_events"))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao editar evento: {e}", "is-danger")

    categories = Category.query.order_by(Category.id).all()

    recurrence = EventRecurrence.query.filter_by(event_id=event.id).first()
    recurrence_weekdays = [rw.weekday.name for rw in recurrence.weekdays] if recurrence else []
    selected_category_ids = [ec.category_id for ec in event.categories]

    return render_template(
        "main/edit_event.html",
        event=event,
        occurrence=occurrence,
        address=address,
        recurrence=recurrence,
        recurrence_weekdays=recurrence_weekdays,
        selected_category_ids=selected_category_ids,
        organizations=orgs,
        categories=categories,
    )


@main_bp.route("/evento/<int:event_id>/excluir", methods=["POST"])
@login_required
def delete_event(event_id):
    if current_user.type != UserType.ORGANIZER:
        abort(403)

    event = Event.query.get_or_404(event_id)

    orgs = [ou.organization for ou in current_user.organizations]
    if event.organization_id not in [o.id for o in orgs]:
        abort(403)

    try:
        for img in event.images:
            if img.url:
                delete_image_by_url(img.url)
        
        db.session.delete(event)
        db.session.commit()

        flash("Evento e todos os dados associados foram excluídos com sucesso!", "is-success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir o evento: {e}", "is-danger")

    return redirect(url_for("main.my_events"))


def _strip_non_digits(value):
    import re
    if value:
        return re.sub(r"\D", "", value)
    return value

@main_bp.route("/perfil", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = _strip_non_digits(request.form.get("phone", ""))
        birth_date_str = request.form.get("birth_date", "")
        cep = _strip_non_digits(request.form.get("cep", ""))
        cpf = _strip_non_digits(request.form.get("cpf", "")) if current_user.type == UserType.ORGANIZER else None
        selected_cats = request.form.getlist("categories")

        try:
            if not name:
                raise ValueError("O nome é obrigatório.")
            if not email:
                raise ValueError("O e-mail é obrigatório.")
            if not phone or len(phone) < 10 or len(phone) > 11:
                raise ValueError("O telefone deve ter entre 10 e 11 dígitos.")
            if not birth_date_str:
                raise ValueError("A data de nascimento é obrigatória.")
            
            birth_date_val = date.fromisoformat(birth_date_str)
            today = date.today()
            if birth_date_val >= today:
                raise ValueError("A data de nascimento deve ser anterior à data atual.")
            
            age = today.year - birth_date_val.year - ((today.month, today.day) < (birth_date_val.month, birth_date_val.day))
            if age < 16:
                raise ValueError("Você precisa ter pelo menos 16 anos para usar o Tô Dentro!.")

            existing_user = User.query.filter_by(email=email).first()
            if existing_user and existing_user.id != current_user.id:
                raise ValueError("Este e-mail já está sendo utilizado por outra conta.")

            if current_user.type == UserType.ORGANIZER:
                if not cpf:
                    raise ValueError("O CPF é obrigatório para produtores.")
                if len(cpf) != 11:
                    raise ValueError("O CPF deve conter exatamente 11 dígitos.")
                existing_cpf = User.query.filter_by(cpf=cpf).first()
                if existing_cpf and existing_cpf.id != current_user.id:
                    raise ValueError("Este CPF já está sendo utilizado por outra conta.")

            dados_cep = None
            if cep:
                if len(cep) != 8:
                    raise ValueError("O CEP deve conter exatamente 8 dígitos.")
                dados_cep = buscar_endereco_por_cep(cep)
                if not dados_cep:
                    raise ValueError("CEP inválido ou não encontrado.")

            if len(selected_cats) > 10:
                raise ValueError("Você pode selecionar no máximo 10 categorias favoritas.")

            current_user.name = name
            current_user.email = email
            current_user.phone = phone
            current_user.birth_date = birth_date_val
            if current_user.type == UserType.ORGANIZER:
                current_user.cpf = cpf

            photo_file = request.files.get("photo")
            if photo_file and photo_file.filename != "":
                new_photo_url = upload_image(photo_file)
                if new_photo_url:
                    if current_user.photo_url:
                        delete_image_by_url(current_user.photo_url)
                    current_user.photo_url = new_photo_url

            if cep and dados_cep:
                user_addr = current_user.addresses[0] if current_user.addresses else None
                if user_addr and user_addr.address:
                    addr = user_addr.address
                    addr.cep = cep
                    addr.street = dados_cep["logradouro"]
                    addr.city = dados_cep["cidade"]
                    addr.state = dados_cep["uf"]
                else:
                    addr = Address(
                        street=dados_cep["logradouro"],
                        number="",
                        city=dados_cep["cidade"],
                        state=dados_cep["uf"],
                        cep=cep,
                        country="Brasil"
                    )
                    db.session.add(addr)
                    db.session.flush()
                    db.session.add(UserAddress(user_id=current_user.id, address_id=addr.id))

            UserCategory.query.filter_by(user_id=current_user.id).delete()
            db.session.flush()
            
            for cid in selected_cats:
                if cid.isdigit():
                    db.session.add(UserCategory(user_id=current_user.id, category_id=int(cid)))

            db.session.commit()
            flash("Perfil atualizado com sucesso!", "is-success")
            return redirect(url_for("main.profile"))

        except ValueError as e:
            db.session.rollback()
            flash(str(e), "is-danger")
        except Exception as e:
            db.session.rollback()
            flash(f"Ocorreu um erro ao atualizar o perfil: {e}", "is-danger")

    categories = Category.query.order_by(Category.id).all()
    user_cep = obter_cep_usuario(current_user) or ""
    selected_category_ids = [uc.category_id for uc in current_user.categories]

    return render_template(
        "main/profile.html",
        categories=categories,
        user_cep=user_cep,
        selected_category_ids=selected_category_ids
    )

@main_bp.route("/minhas-organizacoes")
@login_required
def my_organizations():
    if current_user.type != UserType.ORGANIZER:
        abort(403)

    orgs = [ou.organization for ou in current_user.organizations]
    categories = Category.query.order_by(Category.id).all()
    municipios = _buscar_todos_municipios_ibge()

    return render_template(
        "main/my_organizations.html",
        organizations=orgs,
        categories=categories,
        municipios=municipios,
    )


@main_bp.route("/api/minhas-organizacoes/buscar")
@login_required
def api_buscar_minhas_organizacoes():
    if current_user.type != UserType.ORGANIZER:
        return jsonify({"error": "Acesso não autorizado."}), 403

    org_ids = [ou.organization_id for ou in current_user.organizations]
    if not org_ids:
        return jsonify({"organizacoes": [], "total": 0})

    q = request.args.get("q", "").strip() or None
    cnpj_filter = request.args.get("cnpj", "").strip() or None
    email_filter = request.args.get("email", "").strip() or None
    page = int(request.args.get("page", 1))
    page_size = 15

    query = Organization.query.filter(Organization.id.in_(org_ids))

    if q:
        termo = f"%{q}%"
        query = query.filter(Organization.name.ilike(termo))

    if cnpj_filter:
        cnpj_limpo = _strip_non_digits(cnpj_filter)
        if cnpj_limpo:
            query = query.filter(Organization.cnpj.ilike(f"%{cnpj_limpo}%"))

    if email_filter:
        query = query.filter(Organization.email.ilike(f"%{email_filter}%"))

    query = query.distinct()
    total = query.count()
    orgs_pagina = (
        query.order_by(Organization.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    orgs_json = []
    for org in orgs_pagina:
        orgs_json.append({
            "id": org.id,
            "name": org.name,
            "cnpj": org.cnpj,
            "email": org.email,
            "photo_url": org.photo_url,
        })

    return jsonify(
        {
            "organizacoes": orgs_json,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": (page * page_size) < total,
            "has_prev": page > 1,
        }
    )


@main_bp.route("/criar-organizacao", methods=["GET", "POST"])
@login_required
def create_organization():
    if current_user.type != UserType.ORGANIZER:
        abort(403)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        cnpj_raw = request.form.get("cnpj", "").strip()
        cnpj = _strip_non_digits(cnpj_raw)

        try:
            if not name:
                raise ValueError("O nome da organização é obrigatório.")
            if not email:
                raise ValueError("O e-mail é obrigatório.")
            if len(cnpj) != 14:
                raise ValueError("O CNPJ deve conter exatamente 14 dígitos.")
                
            existing_cnpj = Organization.query.filter_by(cnpj=cnpj).first()
            if existing_cnpj:
                raise ValueError("Este CNPJ já está cadastrado em outra organização.")

            existing_email = Organization.query.filter_by(email=email).first()
            if existing_email:
                raise ValueError("Este e-mail já está sendo utilizado por outra organização.")

            org = Organization(name=name, email=email, cnpj=cnpj)
            
            photo_file = request.files.get("photo")
            if photo_file and photo_file.filename != "":
                photo_url = upload_image(photo_file)
                if photo_url:
                    org.photo_url = photo_url

            db.session.add(org)
            db.session.flush()

            org_user = OrganizationUser(user_id=current_user.id, organization_id=org.id, role='owner')
            db.session.add(org_user)

            db.session.commit()
            flash("Organização criada com sucesso!", "is-success")
            return redirect(url_for("main.my_organizations"))

        except ValueError as e:
            db.session.rollback()
            flash(str(e), "is-danger")
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao criar organização: {e}", "is-danger")

    return render_template("main/create_organization.html")


@main_bp.route("/organizacao/<int:org_id>/editar", methods=["GET", "POST"])
@login_required
def edit_organization(org_id):
    if current_user.type != UserType.ORGANIZER:
        abort(403)

    organization = Organization.query.get_or_404(org_id)
    org_user = OrganizationUser.query.filter_by(user_id=current_user.id, organization_id=org_id).first()
    
    if not org_user:
        abort(403)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        cnpj_raw = request.form.get("cnpj", "").strip()
        cnpj = _strip_non_digits(cnpj_raw)
        
        deleted_photo = request.form.get("deleted_photo") == "true"

        try:
            if not name:
                raise ValueError("O nome da organização é obrigatório.")
            if not email:
                raise ValueError("O e-mail é obrigatório.")
            if len(cnpj) != 14:
                raise ValueError("O CNPJ deve conter exatamente 14 dígitos.")
                
            existing_cnpj = Organization.query.filter_by(cnpj=cnpj).first()
            if existing_cnpj and existing_cnpj.id != organization.id:
                raise ValueError("Este CNPJ já está cadastrado em outra organização.")

            existing_email = Organization.query.filter_by(email=email).first()
            if existing_email and existing_email.id != organization.id:
                raise ValueError("Este e-mail já está sendo utilizado por outra organização.")

            organization.name = name
            organization.email = email
            organization.cnpj = cnpj
            
            if deleted_photo and organization.photo_url:
                delete_image_by_url(organization.photo_url)
                organization.photo_url = None

            photo_file = request.files.get("photo")
            if photo_file and photo_file.filename != "":
                new_photo_url = upload_image(photo_file)
                if new_photo_url:
                    if organization.photo_url:
                        delete_image_by_url(organization.photo_url)
                    organization.photo_url = new_photo_url

            db.session.commit()
            flash("Organização atualizada com sucesso!", "is-success")
            return redirect(url_for("main.my_organizations"))

        except ValueError as e:
            db.session.rollback()
            flash(str(e), "is-danger")
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao editar organização: {e}", "is-danger")

    return render_template("main/edit_organization.html", organization=organization)


@main_bp.route("/organizacao/<int:org_id>/excluir", methods=["POST"])
@login_required
def delete_organization(org_id):
    if current_user.type != UserType.ORGANIZER:
        abort(403)

    organization = Organization.query.get_or_404(org_id)
    org_user = OrganizationUser.query.filter_by(user_id=current_user.id, organization_id=org_id).first()
    
    if not org_user:
        abort(403)

    try:
        if organization.photo_url:
            delete_image_by_url(organization.photo_url)
            
        for event in organization.events:
            for img in event.images:
                if img.url:
                    delete_image_by_url(img.url)
        
        db.session.delete(organization)
        db.session.commit()

        flash("Organização e todos os seus eventos foram excluídos com sucesso!", "is-success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir organização: {e}", "is-danger")

    return redirect(url_for("main.my_organizations"))


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
        ],
        'UserType': UserType
    }