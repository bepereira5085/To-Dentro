from datetime import date, datetime

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
from to_dentro.models.follows import Follow
from to_dentro.models.interested_user import InterestedUser
from to_dentro.models.notification import Notification, NotificationType
from to_dentro.models.user import User, UserType
from to_dentro.models.user_address import UserAddress
from to_dentro.models.user_category import UserCategory
from to_dentro.services.cep_service import (
    buscar_endereco_por_cep,
    calcular_proximidade_cep,
    obter_cep_usuario,
)

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


# ---------------------------------------------------------------------------
# Rotas públicas
# ---------------------------------------------------------------------------

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
            if User.query.filter_by(email=form.email.data.strip().lower()).first():
                session["register_form_data"] = request.form.to_dict()
                session["register_form_errors"] = {
                    "email": [
                        "Este e-mail já está cadastrado. Tente fazer login ou informe outro e-mail."
                    ]
                }
                return redirect(url_for("main.register"))

            user_type = (
                UserType.ORGANIZER
                if form.user_type.data == "ORGANIZER"
                else UserType.REGULAR
            )
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
                    user_address = UserAddress(
                        user_id=user.id, address_id=address.id
                    )
                    db.session.add(user_address)

                db.session.commit()
                login_user(user)
                return redirect(url_for("main.home"))
            except Exception:
                db.session.rollback()
                session["register_form_data"] = request.form.to_dict()
                return redirect(url_for("main.register"))
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
        form = RegisterForm()

    return render_template("main/register.html", form=form)


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
        # TODO: adicionar suporte a foto de perfil quando o campo for adicionado ao banco
        "photo_url": None,
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
        # TODO: retornar foto de perfil quando o campo for adicionado ao banco
        "photo_url": None,
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
            # TODO: adicionar foto de perfil quando o campo for adicionado ao banco
            "photo_url": None,
        }
        for u in usuarios
    ])


@main_bp.route("/api/usuarios/buscar")
@login_required
def api_buscar_usuarios():
    """Busca usuários que o logado ainda não segue (para 'Encontrar amigos')."""
    q = request.args.get("q", "").strip()

    seguindo_ids = [f.following_id for f in current_user.following]
    seguindo_ids.append(current_user.id)  # excluir o próprio usuário

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
            # TODO: adicionar foto de perfil quando o campo for adicionado ao banco
            "photo_url": None,
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

    # Cria notificação para o usuário seguido
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