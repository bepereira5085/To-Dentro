import pytest
from datetime import date
from to_dentro.models.user import User, UserType
from to_dentro.models.hangout_poll import HangoutPoll, HangoutPollOption
from to_dentro.models.notification import Notification, NotificationType
from to_dentro.models.follows import Follow

def test_poll_invitation_model(db):

    user1 = User(name="User One", email="user1@example.com", phone="27999991111", birth_date=date(1995, 1, 1), type=UserType.REGULAR)
    user1.set_password("password123")
    user2 = User(name="User Two", email="user2@example.com", phone="27999992222", birth_date=date(1995, 1, 1), type=UserType.REGULAR)
    user2.set_password("password123")
    db.session.add_all([user1, user2])
    db.session.commit()


    poll = HangoutPoll(title="Test Poll", description="Description", creator_id=user1.id)
    db.session.add(poll)
    db.session.commit()

    notif = Notification(
        actor_user_id=user1.id,
        recipient_user_id=user2.id,
        poll_id=poll.id,
        type=NotificationType.POLL_INVITATION
    )
    db.session.add(notif)
    db.session.commit()

    retrieved = Notification.query.filter_by(recipient_user_id=user2.id).first()
    assert retrieved is not None
    assert retrieved.type == NotificationType.POLL_INVITATION
    assert retrieved.poll_id == poll.id
    assert retrieved.poll.title == "Test Poll"

def test_list_polls_requires_login(client):
    response = client.get("/enquetes")
    assert response.status_code == 302
    assert "/login" in response.headers.get("Location", "")

def test_polls_dashboard(client, db):
    user1 = User(name="User One", email="user1@example.com", phone="27999991111", birth_date=date(1995, 1, 1), type=UserType.REGULAR)
    user1.set_password("password123")
    user2 = User(name="User Two", email="user2@example.com", phone="27999992222", birth_date=date(1995, 1, 1), type=UserType.REGULAR)
    user2.set_password("password123")
    db.session.add_all([user1, user2])
    db.session.commit()

    client.post("/login", data={"email": "user1@example.com", "password": "password123"})

    resp = client.get("/enquetes")
    assert resp.status_code == 200
    assert b"Painel de Enquetes" in resp.data

    poll1 = HangoutPoll(title="My Created Poll", description="A special poll description", creator_id=user1.id)
    db.session.add(poll1)
    db.session.commit()
    resp = client.get("/enquetes")
    assert resp.status_code == 200
    assert b"My Created Poll" in resp.data

def test_invite_friend_api(client, db):
    user1 = User(name="User One", email="user1@example.com", phone="27999991111", birth_date=date(1995, 1, 1), type=UserType.REGULAR)
    user1.set_password("password123")
    user2 = User(name="User Two", email="user2@example.com", phone="27999992222", birth_date=date(1995, 1, 1), type=UserType.REGULAR)
    user2.set_password("password123")
    db.session.add_all([user1, user2])
    db.session.commit()

    follow = Follow(follower_id=user1.id, following_id=user2.id)
    db.session.add(follow)
    db.session.commit()

    poll = HangoutPoll(title="Birthday Party", description="Decide date", creator_id=user1.id)
    db.session.add(poll)
    db.session.commit()

    client.post("/login", data={"email": "user1@example.com", "password": "password123"})

    resp = client.post(
        f"/api/enquete/{poll.uuid}/convidar",
        json={"friend_ids": [user2.id]}
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["sent_count"] == 1

    client.post("/login", data={"email": "user2@example.com", "password": "password123"})
    
    resp = client.get("/api/notificacoes")
    assert resp.status_code == 200
    notif_data = resp.get_json()
    assert notif_data["total"] == 1
    assert "te convidou para votar na enquete: Birthday Party" in notif_data["notificacoes"][0]["mensagem"]
    assert notif_data["notificacoes"][0]["poll_uuid"] == poll.uuid
