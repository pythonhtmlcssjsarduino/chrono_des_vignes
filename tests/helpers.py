from datetime import datetime
from typing import Any

from flask import Flask
from flask.testing import FlaskClient

from chrono_des_vignes import bcrypt, db
from chrono_des_vignes.models import Edition, Event, Inscription, User


def create_admin_user(
    app: Flask,
    username: str = "admin",
    password: str = "AdminPass123!",
    name: str = "Admin",
    lastname: str = "User",
    email: str = "admin@example.com",
) -> tuple[str, str]:
    with app.app_context():
        hashed = bcrypt.generate_password_hash(password).decode("utf-8")
        user = User(
            name=name,
            lastname=lastname,
            username=username,
            email=email,
            phone=None,
            datenaiss=datetime(1990, 1, 1),
            password=hashed,
            admin=True,
        )
        db.session.add(user)
        db.session.commit()
    return username, password


def get_event_id(app: Flask, event_name: str) -> int:
    with app.app_context():
        event = Event.query().filter_by(name=event_name).first()
        assert event is not None, f"Event {event_name} not found"
        return event.id


def get_edition_id(app: Flask, event_name: str, edition_name: str) -> int:
    with app.app_context():
        edition = (
            Edition.query()
            .join(Edition.event)
            .filter(Event.name == event_name, Edition.name == edition_name)
            .first()
        )
        assert edition is not None, f"Edition {edition_name} not found"
        return edition.id


def get_inscription_dossard(
    app: Flask, user_name: str, user_lastname: str, event_name: str, edition_name: str
) -> int | None:
    with app.app_context():
        user = User.query().filter_by(name=user_name, lastname=user_lastname).first()
        if user is None:
            return None
        inscription = user.inscriptions.filter(
            Inscription.event.has(Event.name == event_name),
            Inscription.edition.has(Edition.name == edition_name),
        ).first()
        return inscription.dossard if inscription is not None else None


def login_user(client: FlaskClient, username: str, password: str):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def logout_user(client: FlaskClient):
    return client.get("/logout", follow_redirects=False)


def create_event(client: FlaskClient, event_name: str):
    return client.post(
        "/admin/event/new", data={"name": event_name}, follow_redirects=False
    )


def generate_parcours_data(
    event_id: int, parcours_name: str, parcours_id: int
) -> dict[str, Any]:
    return {
        "creation_date": "2026-04-06T16:05:18",
        "description": "",
        "event_id": event_id,
        "id": parcours_id,
        "modif": True,
        "modif_allowed": True,
        "name": parcours_name,
        "segments": [
            {
                "id": 54,
                "index": 0,
                "start": 42,
                "to": 42,
                "trace": [
                    [52.03897658307622, 12.26336934826194, None],
                    [49.937079756975294, 25.935084350773252, None],
                    [44.4808302785626, 27.12201780758292, None],
                    [41.78769700539063, 16.263774702694505, None],
                    [47.65058757118736, 18.329918127511313, None],
                ],
            }
        ],
        "stands": [
            {
                "chrono": True,
                "color": "#00ff00",
                "ele": None,
                "id": 42,
                "lat": 46.9353,
                "lng": 6.58897,
                "name": "depart",
            }
        ],
    }


def create_parcours(
    client: FlaskClient, event_id: int, parcours_name: str
) -> tuple[dict[str, Any], int]:
    response = client.post(
        f"/api/v1/parcours/create_parcours/{event_id}",
        data={"name": parcours_name},
        follow_redirects=False,
    )
    data = response.get_json()
    assert data is not None, "Failed to create parcours"
    assert data.get("success") is True, (
        f"Failed to create parcours: {data.get('error', 'Unknown error')}"
    )

    response = client.put(
        f"/api/v1/parcours/update_parcours/{event_id}/{data['parcours_id']}",
        json=generate_parcours_data(event_id, parcours_name, data["parcours_id"]),
        follow_redirects=False,
    )
    assert response.status_code == 200, (
        f"Failed to update parcours: {response.data.decode()}"
    )
    assert response.get_json().get("success") is True, (
        f"Failed to update parcours: {response.get_json().get('error', 'Unknown error')}"
    )
    stand_id = response.get_json().get("ids").get("42")
    assert stand_id is not None, "Failed to retrieve stand ID for parcours"
    return data, stand_id


def create_edition(
    client: FlaskClient,
    event_name: str,
    edition_name: str,
    parcours_value: str,
    first_inscription: datetime,
    last_inscription: datetime,
    edition_date: datetime,
):
    return client.post(
        f"/admin/event/{event_name}/editions",
        data={
            "name": edition_name,
            "edition_date": edition_date.strftime("%Y-%m-%dT%H:%M"),
            "description": "Automated test edition",
            "parcours": [parcours_value],
            "first_inscription": first_inscription.strftime("%Y-%m-%dT%H:%M"),
            "last_inscription": last_inscription.strftime("%Y-%m-%dT%H:%M"),
            "rdv_lat": "46.5",
            "rdv_lng": "6.4",
        },
        follow_redirects=False,
    )


def register_for_event(
    client: FlaskClient,
    event_name: str,
    edition_name: str,
    name: str,
    lastname: str,
    email: str,
    phone: str,
    datenaiss: datetime,
    parcours_value: str,
    password: str,
):
    return client.post(
        f"/users/{event_name}/edition/{edition_name}/inscription",
        data={
            "name": name,
            "lastname": lastname,
            "email": email,
            "phone": phone,
            "datenaiss": datenaiss.strftime("%Y-%m-%d"),
            "parcours": [parcours_value],
            "comment": "Automated registration",
            "password": password,
            "repeatpassword": password,
        },
        follow_redirects=False,
    )


def generate_dossards(client: FlaskClient, event_name: str, edition_name: str):
    return client.get(
        f"/event/{event_name}/editions/{edition_name}/dossard/generate",
        follow_redirects=False,
    )


def create_passage_key(
    client: FlaskClient,
    event_id: int,
    edition_id: int,
    name: str,
    stand_ids: list[int] | None = None,
) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/passages/create_key/{event_id}/{edition_id}",
        json={"name": name},
        follow_redirects=False,
    )
    assert response.status_code == 200

    key_data = response.get_json()

    assert key_data is not None, "Failed to create passage key"
    assert key_data["key"] is not None, "Key not returned in response"

    # If stand_ids are provided, update the key with the stand IDs
    if stand_ids:
        update_response = client.put(
            "/api/v1/passages/edit_key",
            json={"id": key_data["id"], "stand_ids": stand_ids},
            follow_redirects=False,
        )
        assert update_response.status_code == 200, (
            "Failed to update passage key with stand IDs"
        )
        updated_key_data = update_response.get_json()
        assert updated_key_data["success"], "Failed to get updated key data"

    return key_data


def record_passage(
    client: FlaskClient, bib: int, key: str, timestamp: datetime
) -> dict[str, Any]:
    response = client.put(
        "/api/v1/chrono/passages",
        json={
            "id": -1,
            "bib": bib,
            "timestamp": timestamp.isoformat(),
            "key": key,
            "last_modified": timestamp.isoformat(),
            "status": "pending",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200, (
        f"Failed to record passage: {response.data.decode()}"
    )
    return response.get_json() or {}


def get_passages_by_key(client: FlaskClient, key: str) -> list[dict[str, Any]]:
    response = client.get(f"/api/v1/chrono/passages/{key}")
    return response.get_json() or []


def format_parcours_choice(name: str, description: str = "") -> str:
    return str((name, description))
