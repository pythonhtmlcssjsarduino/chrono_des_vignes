from datetime import datetime, timedelta

import pytest
from flask import Flask
from flask.testing import FlaskClient
from helpers import (
    create_admin_user,
    create_edition,
    create_event,
    create_parcours,
    create_passage_key,
    format_parcours_choice,
    generate_dossards,
    get_edition_id,
    get_event_id,
    get_inscription_dossard,
    get_passages_by_key,
    login_user,
    logout_user,
    record_passage,
    register_for_event,
)


@pytest.mark.usefixtures("redis_sse")
def test_full_user_workflow(client: FlaskClient, app: Flask):
    admin_username, admin_password = create_admin_user(app)

    login_response = login_user(client, admin_username, admin_password)
    assert login_response.status_code == 302

    event_name = "TestEvent"
    event_response = create_event(client, event_name)
    assert event_response.status_code == 302

    event_id = get_event_id(app, event_name)
    parcours_name = "TestParcours"
    (parcours_data, stand_id) = create_parcours(client, event_id, parcours_name)
    assert parcours_data.get("success") is True
    parcours_value = format_parcours_choice(parcours_name)

    edition_name = "TestEdition"
    now = datetime.now()
    edition_response = create_edition(
        client,
        event_name,
        edition_name,
        parcours_value,
        first_inscription=now - timedelta(hours=1),
        last_inscription=now + timedelta(days=1),
        edition_date=now + timedelta(days=2),
    )
    assert edition_response.status_code == 302

    logout_response = logout_user(client)
    assert logout_response.status_code == 302

    participant_name = "Racer"
    participant_lastname = "Tester"
    registration_response = register_for_event(
        client,
        event_name,
        edition_name,
        participant_name,
        participant_lastname,
        "racer@example.com",
        "0123456789",
        datenaiss=datetime(1995, 1, 1),
        parcours_value=parcours_value,
        password="UserPass123!",
    )
    assert registration_response.status_code == 302

    logout_response = logout_user(client)
    assert logout_response.status_code == 302

    login_response = login_user(client, admin_username, admin_password)
    assert login_response.status_code == 302

    generate_response = generate_dossards(client, event_name, edition_name)
    assert generate_response.status_code == 302

    dossard = get_inscription_dossard(
        app, participant_name, participant_lastname, event_name, edition_name
    )
    assert dossard is not None

    edition_id = get_edition_id(app, event_name, edition_name)

    key_data = create_passage_key(client, event_id, edition_id, "Test Key", [stand_id])
    assert key_data.get("key")
    key = key_data["key"]

    print(f"Generated passage key: {key}")

    # start the parcours
    start_response = client.post(
        f"/api/v1/run_control/launch_parcours/{event_id}/{edition_id}/{parcours_data['parcours_id']}",
        json={"timestamp": (datetime.now() - timedelta(minutes=3)).isoformat()},
        follow_redirects=False,
    )
    assert start_response.status_code == 200
    assert start_response.get_json().get("success") is True, (
        f"Failed to start parcours: {start_response.get_json().get('error', 'Unknown error')}"
    )

    passage_data = record_passage(client, dossard, key, datetime.now())
    assert passage_data.get("success") is True
    assert passage_data["action"]["status"] == "synced"

    passages = get_passages_by_key(client, key)
    assert len(passages) == 1
    assert passages[0]["bib"] == dossard
