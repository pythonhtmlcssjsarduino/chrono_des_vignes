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

from flask import Blueprint, jsonify, redirect, render_template, flash, request, session
from icecream import ic
from chrono_des_vignes import (
    admin_required,
    db,
    set_route,
    lang_url_for as url_for,
    socketio,
)
from chrono_des_vignes.api import ApiBlueprint
from chrono_des_vignes.lib import assert404, calc_points_dist
from flask_login import login_required, current_user
from chrono_des_vignes.models import (
    Event,
    Edition,
    PassageKey,
    Stand,
    ParcoursVersion,
    Passage,
    Inscription,
    Trace,
)
from datetime import datetime
from .form import NewKeyForm, ChronoLoginForm
import secrets
from flask_socketio import join_room, leave_room, emit
from flask_babel import _
from werkzeug.wrappers.response import Response
from typing import Any, TypedDict, cast
from pydantic import BaseModel
from flask_pydantic import validate

passages = Blueprint("passages", __name__, template_folder="templates")
passages_api = ApiBlueprint.admin("passages", version="v1")


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

    passages = (
        Passage.query().filter(Passage.key.has(PassageKey.edition == edition)).all()
    )

    return render_template(
        "dashboard.html",
        event_data=event,
        edition_data=edition,
        user_data=user,
        now=datetime.now(),
        passages=passages,
        event_modif=True,
        edition_sidebar=True,
    )


@login_required
@admin_required
@set_route(passages, "/event/<event_name>/editions/<edition_name>/delete/<key_id>")
def delete_key(event_name: str, edition_name: str, key_id: int) -> str | Response:
    key: PassageKey = PassageKey.query().filter_by(id=key_id).first_or_404()
    if key.edition.edition_date <= datetime.now():
        flash(_("flash.key_not_deleted_edition_passed"), "danger")
        return redirect(
            url_for(
                "admin.editions.passages.dashboard",
                event_name=event_name,
                edition_name=edition_name,
            )
        )
    elif key.passages.count() == 0:
        db.session.delete(key)
        db.session.commit()
        flash(_("flash.key_deleted"), "success")
        return redirect(
            url_for(
                "admin.editions.passages.dashboard",
                event_name=event_name,
                edition_name=edition_name,
            )
        )
    else:
        flash(_("flash.key_not_deleted"), "danger")
        return redirect(
            url_for(
                "admin.editions.passages.dashboard",
                event_name=key.event.name,
                edition_name=key.edition.name,
            )
        )


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


def parcours_chrono_list_dist(parcours: ParcoursVersion, dist_stand: list[int]) -> None:
    part_list: list[Stand] = []
    dist_list: list[float] = []
    start = parcours.start_stand
    new_stand = start
    last_point = None
    dist: float = 0
    # si aucun depart alors ne mettre aucun stand
    if start:
        part_list.append(start)
        turn_nb = 0
        while True:
            if new_stand == start:
                turn_nb += 1
            old_stand = new_stand
            # si l'ancien stand a une trace qui part d lui
            trace = assert404(old_stand.start_trace.filter_by(turn_nb=turn_nb).first())
            if trace:
                new_stand = trace.end
                dist += (
                    calc_points_dist(
                        new_stand.lat, new_stand.lng, last_point[0], last_point[1]
                    )
                    if last_point
                    else 0.0
                )
                last_point = new_stand.lat, new_stand.lng

                if new_stand.id == dist_stand[0]:
                    dist_stand = dist_stand[1:]
                    dist_list.append(dist)
                    if len(dist_stand) == 0:
                        break

                dist += trace.get_dist()
            else:
                break


class StandData(TypedDict):
    stand: Stand | dict[str, Any]
    dist: float
    delta: str | None
    success: bool | None
    current: bool | None


class PassageData(TypedDict):
    dossard: int | None
    name: str
    time_stamp: datetime | float
    parcours: list[StandData]


def get_passage_data(passage: Passage, json: bool = False):
    data: PassageData = {
        "dossard": passage.inscription.dossard,
        "name": passage.inscription.inscrit.name,
        "time_stamp": passage.time_stamp
        if not json
        else passage.time_stamp.timestamp(),
        "parcours": [],
    }
    ic(passage.inscription, passage, passage.id)

    user_passages: list[Passage] = (
        Passage.query()
        .filter(
            Passage.inscription == passage.inscription,
            Passage.time_stamp <= passage.time_stamp,
        )
        .all()
    )
    if len(user_passages) > 0:
        first_passage = user_passages[0]
        current = False
        for stand, dist in zip(
            passage.inscription.parcours.iter_chrono_list(),
            passage.inscription.parcours.get_chrono_dists(),
        ):
            if len(user_passages) > 0 and stand == user_passages[0].get_stand():
                delta = user_passages[0].time_stamp - first_passage.time_stamp
                days = delta.days
                hours, remainder = divmod(delta.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                delta = f"{f'{days} days, ' if days > 0 else ''}{hours:02}:{minutes:02}:{seconds:02}"
                user_passages.pop(0)
                success = True
            elif len(user_passages) > 0:
                delta = None
                success = False
            else:
                if not current:
                    current = True
                    data["parcours"][-1]["current"] = True
                success = None
                delta = None

            data["parcours"].append(
                {
                    "stand": stand if not json else {"name": stand.name},
                    "dist": round(dist, 3),
                    "delta": delta,
                    "success": success,
                    "current": False,
                }
            )
        for p in user_passages:
            success = None
            delta = p.time_stamp - first_passage.time_stamp
            days = delta.days
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            delta = f"{f'{days} days, ' if days > 0 else ''}{hours:02}:{minutes:02}:{seconds:02}"
            ic(p, p.get_stand(), p.key.stands.all(), p.inscription.parcours)  # noqa: F821
            data["parcours"].append(
                {
                    "stand": p.get_stand()
                    if not json
                    else {"name": p.get_stand().name},
                    "dist": None,
                    "delta": delta,
                    "success": success,
                }
            )
        if not current:
            data["parcours"][-1]["current"] = True
    return data


def get_key_passage_data(key: PassageKey, json: bool = False):
    data: list[PassageData] = []
    passage: Passage
    for passage in (
        Passage.query().filter_by(key=key).order_by(Passage.time_stamp.asc()).all()
    ):
        data.append(get_passage_data(passage, json=json))
    return data


@set_route(passages, "/chrono/<key_code>")
def chrono_page(key_code: str) -> str | Response:
    user = current_user if current_user.is_authenticated else None
    key = PassageKey.query().filter_by(key=key_code).first_or_404()
    # TODO uncomment this part
    """ if key.edition.edition_date > datetime.now():
        flash('l\'edition n\'est pas aujourd\'hui', 'warning')
        return redirect(url_for("admin.editions.passages.chrono_home")) """

    return render_template("chrono.html", user_data=user, key=key)


@socketio.on("connect", namespace="/dashboard")
def dashboard_connect(auth: dict[str, Any]) -> bool:
    if (
        current_user.is_authenticated
        and auth.get("event_id")
        and auth.get("edition_id")
    ):
        event = Event.query().get(auth["event_id"])
        if not event or event.createur != current_user:
            return False  # connection not allowed
        edition = event.editions.filter_by(id=auth["edition_id"]).first()
        if not edition:
            return False  # connection not allowed

        session["room"] = f"{event.id}-{edition.id}"
        join_room(session["room"], request.sid)

    else:
        return False  # connection not allowed
    return True


@socketio.on("disconnect", namespace="/dashboard")
def dashboard_disconnect() -> None:
    leave_room(session["room"], request.sid)
    del session["room"]


@socketio.on("connect", namespace="/key")
def key_connect(auth: dict[str, Any]) -> bool:
    if not auth.get("key", False):
        return False  # connection not allowed
    session["room"] = auth["key"]
    join_room(session["room"], request.sid)
    return True


@socketio.on("disconnect", namespace="/key")
def key_disconnect() -> None:
    leave_room(session["room"], request.sid)
    del session["room"]


@socketio.on("get_passages", namespace="/key")
def get_passages_data():
    key = PassageKey.query().filter_by(key=session["room"]).first()
    if key:
        return get_key_passage_data(key, json=True)


@socketio.on("set_passage", namespace="/key")
def set_passage(data: dict[str, Any]) -> None:
    key = PassageKey.query().filter_by(key=session["room"]).first()
    if not key:
        emit(
            "passage_response",
            {
                "success": False,
                "saved": False,
                "error": "not valide key",
                "request": data,
            },
            to=session["room"],
        )
        return

    inscription = (
        Inscription.query()
        .filter(
            Inscription.dossard == cast(int, data["dossard"]),
            Inscription.edition == key.edition,
        )
        .first()
    )
    if not inscription:
        emit(
            "passage_response",
            {
                "success": False,
                "saved": False,
                "error": "not valide dossard",
                "request": data,
            },
            to=session["room"],
        )
        return
    if inscription.passages.count() <= 0:
        emit(
            "passage_response",
            {
                "success": False,
                "saved": False,
                "error": "edition not started",
                "request": data,
            },
            to=session["room"],
        )
        return

    if inscription.end == "finish":
        emit(
            "passage_response",
            {
                "success": False,
                "saved": False,
                "error": "has already finish",
                "request": data,
            },
            to=session["room"],
        )
        return
    elif inscription.end == "abandon":
        emit(
            "passage_response",
            {"success": False, "saved": False, "error": "as abandoné", "request": data},
            to=session["room"],
        )
        return
    elif inscription.end == "disqual":
        emit(
            "passage_response",
            {
                "success": False,
                "saved": False,
                "error": "is disqualified",
                "request": data,
            },
            to=session["room"],
        )
        return

    pass_time = datetime.fromtimestamp(cast(float, data["time"]) / 1000)

    passage = Passage(
        key_id=key.id, time_stamp=pass_time, inscription_id=inscription.id
    )
    db.session.add(passage)
    db.session.commit()
    db.session.refresh(passage)

    emit(
        "new_passage",
        {
            "time": str(pass_time),
            "user": inscription.inscrit.username,
            "dossard": inscription.dossard,
            "key": key.name,
            "stand": passage.get_stand().name,
        },
        namespace="/dashboard",
        to=f"{passage.key.event.id}-{passage.key.edition.id}",
    )
    emit(
        "passage_response",
        {
            "success": True,
            "request": data,
            "passage": get_passage_data(passage, json=True),
        },
        to=session["room"],
    )

    first_passage = inscription.passages.order_by(Passage.time_stamp.asc()).first()
    if not first_passage:
        return
    pass_data = get_passage_data(passage, json=True)
    pass_data.update(
        {
            "started": True,
            "parcours_id": inscription.parcours.id,
            "start_time": first_passage.time_stamp.timestamp(),
            "id": inscription.id,
            "finish": inscription.has_finish(),
            "all_right": inscription.has_all_right(),
            "end": inscription.end,
        }
    )
    emit(
        "new_passage",
        pass_data,
        namespace="/edition/parcours",
        to=f"edition-parcours-{inscription.event.id}-{inscription.edition.id}",
    )
