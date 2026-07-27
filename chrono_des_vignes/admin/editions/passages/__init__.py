"""
# Chrono Des Vignes
# a timing system for sports events
#
# Copyright © 2024-2026 Romain Maurer
# This file is part of Chrono Des Vignes
#
# Chrono Des Vignes is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version.
#
# Chrono Des Vignes is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Foobar.
# If not, see <https://www.gnu.org/licenses/>.
#
# You may contact me at chrono-des-vignes@ikmail.com
"""

import random
import secrets
from datetime import datetime, timedelta
from typing import Literal

from flask import Blueprint, abort, jsonify, redirect, render_template, request
from flask_login import current_user, login_required
from flask_pydantic import validate
from flask_sse import sse
from icecream import ic
from pydantic import BaseModel
from werkzeug.wrappers.response import Response

from chrono_des_vignes import (
    admin_required,
    db,
    set_route,
)
from chrono_des_vignes import (
    lang_url_for as url_for,
)
from chrono_des_vignes.api import ApiBlueprint
from chrono_des_vignes.lib import assert404
from chrono_des_vignes.models import (
    Edition,
    Event,
    Inscription,
    ParcoursVersion,
    Passage,
    PassageKey,
    Stand,
)

from .form import ChronoLoginForm

passages = Blueprint("passages", __name__, template_folder="templates")
passages_api = ApiBlueprint.admin("passages", version="v1")
chrono_api = ApiBlueprint("chrono", version="v1")


@passages_api.route("/list_keys/<int:edition_id>/<int:event_id>")
def get_keys(edition_id: int, event_id: int):
    keys = PassageKey.query().filter_by(edition_id=edition_id, event_id=event_id).all()
    return {
        "keys": [
            {
                "id": key.id,
                "name": key.name,
                "key": key.key,
                "passages": key.passages.count(),
                "stands": [
                    {"id": s.id, "name": s.name, "parcours": s.parcours_version.name}
                    for s in key.stands
                ],
            }
            for key in keys
        ]
    }


def generate_pronounceable_key(num_syllables: int = 3):
    consonants = "bcdfghjklmnpqrstvwxyz"
    vowels = "aeiou"
    syllables: list[str] = []
    for _i in range(num_syllables):
        c1 = secrets.choice(consonants)
        v = secrets.choice(vowels)
        c2 = secrets.choice(consonants)
        syllables.append(f"{c1}{v}{c2}")
    return "-".join(syllables).upper()


@passages_api.route("/create_key/<int:event_id>/<int:edition_id>", method="POST")
def create_key(event_id: int, edition_id: int):
    key_code = generate_pronounceable_key()
    while PassageKey.query().filter_by(key=key_code).first():
        key_code = generate_pronounceable_key()
    key = PassageKey(
        event_id=event_id,
        edition_id=edition_id,
        key=key_code,
        name=request.get_json().get("name", ""),  # pyright: ignore[reportAny]
    )
    db.session.add(key)
    db.session.commit()
    return jsonify({"id": key.id, "key": key.key})


@passages_api.route("/delete_key/<int:key_id>", method="DELETE")
def delete_key_api(key_id: int):
    # check if the user is admin and the key exist
    key: PassageKey = PassageKey.query().get_or_404(key_id)
    if key.event.createur.id != current_user.id:
        return jsonify({"success": False, "error": "not allowed"})
    if key.passages.count() == 0:
        db.session.delete(key)
        db.session.commit()
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "key has passages"})


class EditKeyRequest(BaseModel):
    id: int
    name: str | None = None
    stands_ids: list[int] | None = None


@passages_api.route("/edit_key", method="PUT")
@validate()
def edit_key_api(body: EditKeyRequest):
    # check if the user is admin and the key exist
    key: PassageKey = PassageKey.query().get_or_404(body.id)
    if key.event.createur.id != current_user.id:
        return jsonify({"success": False, "error": "not allowed"})

    key.name = body.name or key.name
    if body.stands_ids is not None:
        key.stands = (
            Stand.query()
            .filter(
                Stand.id.in_(body.stands_ids),
                Stand.chrono.is_(True),
                Stand.parcours_version.has(
                    ParcoursVersion.editions.any(Edition.id == key.edition_id)
                ),
            )
            .all()
        )

    db.session.commit()
    return jsonify({"success": True})


@passages_api.route("/get_passages/<int:edition_id>/<int:event_id>")
def get_passages_api(edition_id: int, event_id: int):
    event = Event.query().filter_by(id=event_id).first_or_404()
    edition = assert404(event.editions.filter_by(id=edition_id).first())
    passages = (
        Passage.query()
        .filter(Passage.key.has(PassageKey.edition == edition))
        .order_by(Passage.time_stamp.desc())
        .all()
    )
    return jsonify([p.SSE_data() for p in passages])


class TimingAction(BaseModel):
    id: int
    bib: int
    timestamp: datetime
    key: str
    last_modified: datetime
    status: Literal["pending", "synced", "error", "user", "alert"]
    error_type: (
        Literal["invalid_bib", "bib_not_started", "server", "duplicate"] | None
    ) = None
    error_message: str | None = None


def sync_action(body: TimingAction):
    key = PassageKey.query().filter_by(key=body.key).first()
    if not key:
        return abort(400, "invalid key")

    action = body
    action.last_modified = datetime.now()

    # check bib state
    inscription = (
        Inscription.query()
        .filter_by(dossard=action.bib, edition_id=key.edition.id)
        .first()
    )
    if inscription is None:
        action.status = "user"
        action.error_type = "invalid_bib"
        action.error_message = "numero de dossard invalid"
        return action
    elif not inscription.has_started():
        action.status = "user"
        action.error_type = "bib_not_started"
        action.error_message = "numero de dossard pas partit"
        return action
    # check for duplicated record
    recents = inscription.passages.filter(
        Passage.time_stamp > action.timestamp - timedelta(seconds=2)
    ).count()
    if recents > 0:
        action.status = "alert"
        action.error_type = "duplicate"
        action.error_message = "possible duplicata (dernier passage moins de 2s)"
    else:
        action.status = "synced"

    if (passage := Passage.query().get(body.id)) is not None:
        if key.passages.get(body.id) is None:
            return abort(400, "passage assigned to another key")
        # already existing passage

        passage.time_stamp = action.timestamp
        passage.inscription_id = inscription.id
        db.session.commit()

    else:
        # create a new passage
        if body.id > 0:
            return abort(400, "newly created action should have neg id")
        passage = Passage(
            time_stamp=action.timestamp, key_id=key.id, inscription_id=inscription.id
        )
        db.session.add(passage)
        db.session.commit()
        db.session.refresh(passage)
        action.id = passage.id

    sse.publish(
        passage.SSE_data(),
        type="new_passage",
        channel=f"passages_{key.edition.id}_{key.event.id}",
    )
    sse.publish(
        passage.SSE_data(),
        type="new_passage",
        channel=f"run_control_{key.edition.id}_{key.event.id}",
    )

    return action


@chrono_api.route("/passages", method="PUT")
@validate()
def record_passage(body: TimingAction):
    ic(body)
    action = sync_action(body)
    return jsonify({"success": True, "action": action.model_dump()})


@chrono_api.route("/passages/<string:key_str>", method="GET")
def get_passages(key_str: str):
    key = PassageKey.query().filter_by(key=key_str).first_or_404()
    passages = (
        Passage.query()
        .filter(Passage.key == key)
        .order_by(Passage.time_stamp.desc())
        .all()
    )

    def format(passage: Passage) -> TimingAction:
        return TimingAction(
            id=passage.id,
            bib=passage.inscription.dossard or -1,
            timestamp=passage.time_stamp,
            key=passage.key.key if passage.key else "",
            last_modified=passage.time_stamp,
            status="synced",
        )

    return jsonify([format(p).model_dump() for p in passages])


# TODO remove this test route
@set_route(passages, "/push")
def push_passage():
    data = {
        "id": random.randint(1, 1000),
        "time_stamp": datetime.now(),
        "inscription": {
            "id": random.randint(1, 100),
            "dossard": random.randint(1, 100),
            "inscrit": {
                "id": random.randint(1, 100),
                "username": f"User{random.randint(1, 100)}",
            },
        },
        "key": {
            "id": random.randint(1, 100),
            "name": f"Key{random.randint(1, 100)}",
            "key": f"KEY-{random.randint(1000, 9999)}",
        },
        "stand": {
            "id": random.randint(1, 100),
            "name": f"Stand{random.randint(1, 100)}",
        },
    }
    sse.publish(
        data,
        type="new_passage",
        channel="passages_1_1",
    )
    sse.publish(
        data,
        type="new_passage",
        channel="run_control_1_1",
    )
    return "ok"


@login_required
@admin_required
@set_route(
    passages,
    "/event/<event_name>/editions/<edition_name>/dashboard",
    methods=["get", "post"],
)
def dashboard(event_name: str, edition_name: str) -> str | Response:
    user = current_user
    event = Event.query().filter_by(name=event_name).first_or_404()
    edition = assert404(event.editions.filter_by(name=edition_name).first())

    return render_template(
        "dashboard.html",
        event_data=event,
        edition_data=edition,
        user_data=user,
        now=datetime.now(),
        event_modif=True,
        edition_sidebar=True,
    )


@set_route(passages, "/chrono/<key_code>")
def chrono_page(key_code: str) -> str | Response:
    user = current_user if current_user.is_authenticated else None
    key = PassageKey.query().filter_by(key=key_code).first_or_404()

    return render_template("chrono.html", user_data=user, key=key)


@set_route(passages, "/chrono", methods=["GET", "post"])
def chrono_home() -> str | Response:
    user = current_user if current_user.is_authenticated else None

    form: ChronoLoginForm = ChronoLoginForm()
    if form.validate_on_submit():
        if PassageKey.query().filter_by(key=form.key.data).first():
            return redirect(
                url_for("admin.editions.passages.chrono_page", key_code=form.key.data)
            )
        else:
            form.key.errors = list(form.key.errors) + ["cette clé n'est pas valable."]

    return render_template("chrono_home.html", user_data=user, form=form)
