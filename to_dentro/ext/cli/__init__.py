import click
import random
from to_dentro.ext.db import db
from datetime import date, time, timedelta
from to_dentro.models.user import User, UserType
from to_dentro.models.user_category import UserCategory
from to_dentro.models.user_address import UserAddress
from to_dentro.models.follows import Follow
from to_dentro.models.category import Category, Categories
from to_dentro.models.address import Address
from to_dentro.models.organization import Organization
from to_dentro.models.organization_user import OrganizationUser
from to_dentro.models.event import Event
from to_dentro.models.event_occurrence import EventOccurrence
from to_dentro.models.event_image import EventImage
from to_dentro.models.event_category import EventCategories
from to_dentro.models.interested_user import InterestedUser
from to_dentro.models.event_address import EventAddress
from to_dentro.models.event_recurrence import EventRecurrence, RecurrenceTypes, WeeksInterval
from to_dentro.models.event_recurrence_weekday import EventRecurrenceWeekday, WeekDays
from to_dentro.models.notification import Notification, NotificationType

def init_app(app):
    @app.cli.command("createdb")
    def createdb():
        click.echo(click.style("Criando tabelas no banco...", fg="blue"))
        db.create_all()
        click.echo(click.style("Tabelas criadas com sucesso.", fg="green"))

    @app.cli.command("cleardb")
    def cleardb():
        click.echo(click.style("Limpando banco...", fg="red"))
        db.drop_all()
        click.echo(click.style("Banco excluído com sucesso.", fg="green"))

    @app.cli.command("dbseed")
    def dbseed():
        try:
            click.echo(click.style("Iniciando população do banco...", fg="blue"))

            existing_categories = {
                category.type
                for category in Category.query.all()
            }

            categories = [
                Category(type=category)
                for category in Categories
                if category not in existing_categories
            ]

            db.session.add_all(categories)
            db.session.commit()

            addresses = [
                Address(street="Av. Beira Mar", number="1000", city="Vitória", state="ES", cep="29050000", country="Brasil"),
                Address(street="Rua das Acácias", number="15", city="Vila Velha", state="ES", cep="29100100", country="Brasil"),
                Address(street="Rodovia do Sol", number="3500", city="Guarapari", state="ES", cep="29200000", country="Brasil"),
                Address(street="Praça do Papa", number="S/N", city="Vitória", state="ES", cep="29050100", country="Brasil"),
                Address(street="Centro de Convenções", number="50", city="Serra", state="ES", cep="29160000", country="Brasil"),
                Address(street="Rua do Lazer", number="110", city="Domingos Martins", state="ES", cep="29260000", country="Brasil")
            ]
            db.session.add_all(addresses)
            db.session.commit()

            users_seed = [
                ("Alice Souza", "alice@email.com", "11111111111", "27999990001", UserType.REGULAR, date(1995, 3, 15)),
                ("Bruno Costa", "bruno@email.com", "22222222222", "27999990002", UserType.REGULAR, date(1992, 7, 22)),
                ("Carla Mendes", "carla@email.com", "33333333333", "27999990003", UserType.ORGANIZER, date(1988, 11, 5)),
                ("Diego Alves", "diego@email.com", "44444444444", "27999990004", UserType.ORGANIZER, date(1990, 1, 30)),
                ("Elisa Nogueira", "elisa@email.com", "55555555555", "27999990005", UserType.REGULAR, date(1998, 6, 18)),
                ("Felipe Lima", "felipe@email.com", "66666666666", "27999990006", UserType.REGULAR, date(1993, 9, 12)),
                ("Gabriela Rocha", "gabi@email.com", "77777777777", "27999990007", UserType.ORGANIZER, date(1991, 4, 25)),
                ("Henrique Dias", "henrique@email.com", "88888888888", "27999990008", UserType.ORGANIZER, date(1987, 12, 3)),
                ("Isabela Castro", "isabela@email.com", "99999999999", "27999990009", UserType.ORGANIZER, date(1996, 2, 14)),
                ("João Farias", "joao.f@email.com", "10101010101", "27999990010", UserType.REGULAR, date(1994, 8, 7)),
            ]

            users_seed_db_pattern = []
            for _name, _email, _cpf, _phone, _type, _birth_date in users_seed:
                _user = User(name=_name, email=_email, cpf=_cpf, phone=_phone, type=_type, birth_date=_birth_date)
                _user.set_password("12345678")
                users_seed_db_pattern.append(_user)

            db.session.add_all(users_seed_db_pattern)
            db.session.commit()

            db.session.add_all([
                UserAddress(user_id=users_seed_db_pattern[0].id, address_id=addresses[1].id),
                UserAddress(user_id=users_seed_db_pattern[1].id, address_id=addresses[2].id),
                UserCategory(user_id=users_seed_db_pattern[0].id, category_id=categories[0].id),
                UserCategory(user_id=users_seed_db_pattern[1].id, category_id=categories[1].id)
            ])

            db.session.add_all([
                Follow(follower_id=users_seed_db_pattern[0].id, following_id=users_seed_db_pattern[1].id),
                Follow(follower_id=users_seed_db_pattern[1].id, following_id=users_seed_db_pattern[0].id)
            ])
            db.session.commit()

            organizations_seed = [
                ("11111111000111", "Agência Vibe", "contato@vibe.com", users_seed_db_pattern[2]),
                ("22222222000122", "Esportes ES", "atendimento@esportes.com", users_seed_db_pattern[3]),
                ("33333333000133", "Teatro Capixaba", "bilheteria@teatro.com", users_seed_db_pattern[6]),
                ("44444444000144", "Feiras & Cia", "eventos@feiras.com", users_seed_db_pattern[7]),
                ("55555555000155", "Sons da Cidade", "shows@sons.com", users_seed_db_pattern[8])
            ]

            organizations_db_pattern = []
            for cnpj, _name, _email, _owner in organizations_seed:
                org = Organization(cnpj=cnpj, name=_name, email=_email)
                db.session.add(org)
                organizations_db_pattern.append((org, _owner))
            db.session.commit()

            for org, _owner in organizations_db_pattern:
                db.session.add(OrganizationUser(user_id=_owner.id, organization_id=org.id, role="Fundador"))
            db.session.commit()

            events_seed = [
                # Agência Vibe
                {"name": "Luau de Verão", "desc": "Música acústica na areia.", "cat": categories[0], "img": "https://site.com/luau.jpg"},
                {"name": "Festa Neon", "desc": "A melhor festa eletrônica.", "cat": categories[4], "img": "https://site.com/neon.jpg"},
                {"name": "Samba de Roda", "desc": "Samba raiz para a família.", "cat": categories[0], "img": "https://site.com/samba.jpg"},
                # Esportes ES
                {"name": "Corrida Noturna", "desc": "Percurso de 5km e 10km.", "cat": categories[1], "img": "https://site.com/corrida.jpg"},
                {"name": "Torneio de Vôlei", "desc": "Campeonato de vôlei de praia.", "cat": categories[1], "img": "https://site.com/volei.jpg"},
                {"name": "Aulão de Cross", "desc": "Treino pesado ao ar livre.", "cat": categories[1], "img": "https://site.com/cross.jpg"},
                # Teatro Capixaba
                {"name": "Peça: O Auto", "desc": "Comédia clássica em cartaz.", "cat": categories[2], "img": "https://site.com/auto.jpg"},
                {"name": "Show de Mágica", "desc": "Ilusionismo para crianças.", "cat": categories[2], "img": "https://site.com/magica.jpg"},
                {"name": "Stand up Comedy", "desc": "Noite de risadas garantidas.", "cat": categories[2], "img": "https://site.com/standup.jpg"},
                # Feiras & Cia
                {"name": "Feira de Orgânicos", "desc": "Direto do produtor rural.", "cat": categories[3], "img": "https://site.com/organicos.jpg"},
                {"name": "Expo Noivas", "desc": "Tudo para o seu casamento.", "cat": categories[3], "img": "https://site.com/noivas.jpg"},
                {"name": "Bazar Solidário", "desc": "Roupas com alto desconto.", "cat": categories[3], "img": "https://site.com/bazar.jpg"},
                # Sons da Cidade
                {"name": "Festival de Inverno", "desc": "Música e gastronomia fria.", "cat": categories[4], "img": "https://site.com/inverno.jpg"},
                {"name": "Tributo ao Rock", "desc": "Bandas cover clássicas.", "cat": categories[0], "img": "https://site.com/rock.jpg"},
                {"name": "Jazz na Praça", "desc": "Apresentação instrumental.", "cat": categories[0], "img": "https://site.com/jazz.jpg"},
            ]

            created_events = []
            idx = 0

            for org, _ in organizations_db_pattern:
                for _ in range(3):
                    detail = events_seed[idx]
                    is_recurrent = True if idx < 2 else False

                    _event = Event(
                        organization_id=org.id,
                        name=detail["name"],
                        description=detail["desc"],
                        is_recurrent=is_recurrent
                    )
                    db.session.add(_event)
                    db.session.commit()

                    db.session.add(EventCategories(event_id=_event.id, category_id=detail["cat"].id))
                    db.session.add(EventImage(event_id=_event.id, url=detail["img"]))

                    _ocurrence = EventOccurrence(
                        event_id=_event.id,
                        start_date=date.today() + timedelta(days=(idx*5)),
                        start_time=time(18, 0),
                        duration_days=1,
                        interested_count=0,
                        observations="Chegue 1 hora antes."
                    )
                    db.session.add(_ocurrence)
                    db.session.commit()

                    db.session.add(EventAddress(event_occurrence_id=_ocurrence.id, address_id=random.choice(addresses).id))

                    if is_recurrent:
                        _recurrence = EventRecurrence(
                            event_id=_event.id,
                            type=RecurrenceTypes.WEEKLY,
                            start_date=date.today(),
                            weeks_interval=WeeksInterval.ONE
                        )
                        db.session.add(_recurrence)
                        db.session.commit()

                        db.session.add(EventRecurrenceWeekday(
                            recurrence_id=_recurrence.id,
                            weekday=WeekDays.FRIDAY
                        ))

                    created_events.append(_event)
                    idx += 1

            db.session.commit()

            regular_users = [_user for _user in users_seed_db_pattern if _user.type == UserType.REGULAR]

            for ev in created_events[:5]:
                for _user in regular_users[:3]:
                    db.session.add(InterestedUser(user_id=_user.id, event_id=ev.id))
            db.session.commit()

            ocurrence_example = EventOccurrence.query.filter_by(event_id=created_events[0].id).first()
            if ocurrence_example:
                notification = Notification(
                    actor_user_id=users_seed_db_pattern[1].id,
                    recipient_user_id=users_seed_db_pattern[0].id,
                    event_occurrence_id=ocurrence_example.id,
                    type=NotificationType.EVENT_INTERESTED
                )
                db.session.add(notification)
                db.session.commit()

            click.echo(click.style("Seed concluído com sucesso!", fg="green"))

        except Exception as e:
            db.session.rollback()
            click.echo(click.style(f"Erroao realizar o seed: {e}", fg="red"))

    @app.cli.command("makeadmin")
    @click.argument("email")
    def makeadmin(email):
        click.echo(click.style(f"Buscando usuário com o email: {email}...", fg="blue"))
        user = User.query.filter_by(email=email).first()
        if not user:
            click.echo(click.style("Usuário não encontrado.", fg="red"))
            return
        user.is_admin = True
        db.session.commit()
        click.echo(click.style(f"Usuário {user.name} agora é um administrador!", fg="green"))
