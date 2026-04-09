"""
# Chrono Des Vignes
# a timing system for sports events
#
# Copyright © 2025-2026 Romain Maurer
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

from ast import literal_eval
from datetime import datetime
from typing import Any, TypedDict, cast

from colour import Color
from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required
from icecream import ic
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
from chrono_des_vignes.lib import (
    assert404,
    is_valide_name,
)
from chrono_des_vignes.models import (
    Event,
    Parcours,
    ParcoursVersion,
    Stand,
    Trace,
    get_column_max_length,
)


parcours_bp = Blueprint("parcours", __name__, template_folder="templates")
# region api
api = ApiBlueprint.admin("parcours")


class StandData(TypedDict):
    id: int
    name: str
    lat: float
    lng: float
    ele: float | None
    color: str
    chrono: bool


class SegmentData(TypedDict):
    id: int
    start: int
    to: int
    trace: list[tuple[float, float, float | None]]
    index: int


class ParcoursData(TypedDict):
    id: int
    name: str
    description: str
    creation_date: datetime
    stands: list[StandData]
    segments: list[SegmentData]
    modif: bool
    modif_allowed: bool


@api.route("/create_parcours/<int:event_id>", method="POST")
def create_parcours(event_id: int):
    name = request.form.get("name")
    if name is None or not is_valide_name(
        name, get_column_max_length(Parcours, "name"), 0
    ):
        return err("name field is not valid")

    # region create parcours

    # create Parcours Object
    parcours = Parcours(name, event_id)
    db.session.add(parcours)
    db.session.commit()
    db.session.refresh(parcours)
    # create a first version
    version = ParcoursVersion(parcours.id, version="1")
    db.session.add(version)
    db.session.commit()
    db.session.refresh(version)
    # with a first start stand
    stand = Stand("", 1000, 0, version.id)
    db.session.add(stand)
    db.session.commit()

    # endregion
    return jsonify(
        {
            "success": True,
            "parcours_id": parcours.id,
            "url": url_for(
                "admin.parcours.modify_parcours",
                event_name=parcours.event.name,
                parcours_name=parcours.name,
            ),
        }
    )


# region

# endregion


def get[T](obj: dict[str, Any], key: str, t: type[T]):
    if isinstance(p := obj.get(key, None), t):
        return p
    return None


def get_id(obj: dict[str, Any], ids: dict[int, int], key: str = "id"):
    if (id := get(obj, key, int)) is not None:
        return id if id > 0 else ids.get(id, None)
    return None


def err(msg: str, op: dict[str, Any] | None = None, ids: dict[int, int] | None = None):
    return jsonify(
        {
            "success": False,
            "error": msg,
            "op": op,
            "ids": ids,
        }
    )


@api.route("/update_parcours/<int:event_id>/<int:parcours_version_id>", method="PUT")
def update_parcours_put(event_id: int, parcours_version_id: int):
    parcours: ParcoursVersion = (
        ParcoursVersion.query()
        .filter(
            ParcoursVersion.parcours.has(Parcours.event_id == event_id),
            ParcoursVersion.id == parcours_version_id,
        )
        .first_or_404()
    )
    data: Any = request.get_json()  # pyright: ignore[reportAny]

    ic("put", data)
    return jsonify({"success": True})


@api.route("/update_parcours/<int:event_id>/<int:parcours_version_id>", method="POST")
def update_parcours(event_id: int, parcours_version_id: int):
    parcours: ParcoursVersion = (
        ParcoursVersion.query()
        .filter(
            ParcoursVersion.parcours.has(Parcours.event_id == event_id),
            ParcoursVersion.id == parcours_version_id,
        )
        .first_or_404()
    )
    data: Any = request.get_json()  # pyright: ignore[reportAny]

    if not isinstance(data, list):
        return err("data not valid not a list")
    ic(data)  # pyright: ignore[reportUnknownArgumentType]
    ids: dict[int, int] = {}
    alone_stands: dict[int, tuple[float, float]] = {}
    for op in cast(list[dict[str, Any]], data):
        match op.get("op"):
            case "stand:created":
                lat = get(op, "lat", float)
                lng = get(op, "lng", float)
                tempId = get(op, "tempId", int)
                if lat is None or lng is None or tempId is None:
                    return err(
                        "op stand:created data (lat, lng or tempId) was not provided"
                    )

                if (  # premier stand
                    parcours.stands.count() == 1
                    and (stand := parcours.start).lat == 1000
                ):
                    stand.lat = lat
                    stand.lng = lng
                    db.session.commit()
                    ids[tempId] = stand.id
                else:
                    alone_stands[tempId] = (lat, lng)
            case "stand:modif":
                # Validation de l'ID et récupération de l'objet
                stand_id = get(op, "id", int)
                if stand_id is None:
                    return err("id field was not provided")

                stand = (
                    Stand.query()
                    .filter_by(id=(stand_id if stand_id > 0 else ids.get(stand_id, -1)))
                    .first()
                )
                if stand is None:
                    return err(f"stand with id {stand_id} do not exist")

                ## actual modifications
                if (lat := get(op, "lat", float)) is not None:
                    stand.lat = lat
                if (lng := get(op, "lng", float)) is not None:
                    stand.lng = lng
                if (name := get(op, "name", str)) is not None:
                    stand.name = name
                if (color := get(op, "color", str)) is not None:
                    try:
                        stand.color = Color(color)
                    except ValueError:
                        return err(
                            f"{color}) is not a valid color. see https://pypi.org/project/colour/"
                        )
                if (chrono := get(op, "chrono", bool)) is not None:
                    stand.chrono = chrono
            case "segment:created":
                start_id = get_id(op, ids, "from")
                to_id = get(op, "to", int)
                index = get(op, "index", int)
                temp_id = get(op, "tempId", int)

                # 2. Guard Clause: Validate inputs immediately
                if (
                    start_id is None
                    or to_id is None
                    or index is None
                    or temp_id is None
                ):
                    return err(
                        "op segment:created data (from, to, index or tempId) was not provided",
                        op,
                        ids,
                    )

                # check if the start stand is a valid one
                start_stand = (
                    Stand.query()
                    .filter_by(id=start_id, parcours_id=parcours_version_id)
                    .first()
                )
                if start_stand is None:
                    return err(f"stand with id {start_id} do not exist")
                end = alone_stands.pop(to_id, None)
                if end is None:
                    return err("to field does not correspond to an existing stand")
                ic(Trace.query().filter_by(parcours_id=parcours.id).count(), index)
                if (
                    i := Trace.query().filter_by(parcours_id=parcours.id).count()
                ) != index:
                    return err(f"the provided index is not valid (expected index {i})")

                end_stand = Stand(
                    name="", lat=end[0], lng=end[1], parcours_id=parcours.id
                )
                db.session.add(end_stand)
                db.session.commit()
                db.session.refresh(end_stand)
                trace = Trace(
                    index=index,
                    name="",
                    parcours_id=parcours.id,
                    start_id=start_stand.id,
                    end_id=end_stand.id,
                )
                db.session.add(trace)
                db.session.commit()
                db.session.refresh(trace)
                ids[to_id] = end_stand.id
                ids[temp_id] = trace.id

            case "segment:modif":
                id = get_id(op, ids)
                if id is None:
                    return err("id field was not provided or not valid")
                segment = (
                    Trace.query()
                    .filter_by(id=id, parcours_id=parcours_version_id)
                    .first()
                )
                if segment is None:
                    return err(f"no segment with an id {id} found")

                if (trace := Trace.check_path(get(op, "trace", list))) is not None:
                    segment.path = trace
                else:
                    return err("the provided trace is not valid")
                if (to := get(op, "to", int)) is not None and Stand.query().filter_by(
                    parcours_id=parcours_version_id, id=to
                ).first() is not None:
                    segment.end_id = to
            case "stand:deleted":
                id = get_id(op, ids, "id")
                if id is None:
                    return err("id was not provided")
                stand = (
                    Stand.query()
                    .filter_by(
                        parcours_id=parcours_version_id,
                        id=id,
                    )
                    .first()
                )
                if stand is None:
                    return err(f"no stand with an id {id} found")
                if stand.start_trace.count() + stand.end_trace.count() == 0:
                    db.session.delete(stand)
            case _ as o:  # pyright: ignore[reportAny]
                return jsonify(
                    {"success": False, "error": f"op {o} is not a recognise operation"}
                )
        db.session.commit()

    return jsonify({"success": True, "ids": ids})


@api.route("/get_parcours/<int:event_id>/<int:parcours_version_id>")
def get_parcours(event_id: int, parcours_version_id: int):
    parcours = (
        ParcoursVersion.query()
        .filter(
            ParcoursVersion.parcours.has(Parcours.event_id == event_id),
            ParcoursVersion.id == parcours_version_id,
        )
        .first_or_404()
    )
    data: ParcoursData = {
        "id": parcours.id,
        "name": parcours.name,
        "description": parcours.description,
        "creation_date": parcours.creation_date,
        "stands": [],
        "segments": [],
        "modif": True,  # todo : check from the date
        "modif_allowed": True,
    }

    segment_index = 0
    stands_ids = set[int]()
    for etape in parcours:
        if isinstance(etape, Stand):
            if etape.id in stands_ids:
                continue
            stands_ids.add(etape.id)
            data["stands"].append(
                {
                    "id": etape.id,
                    "name": etape.name,
                    "lat": etape.lat,
                    "lng": etape.lng,
                    "ele": etape.elevation,
                    "color": etape.color.get_hex_l(),
                    "chrono": etape.chrono,
                }
            )
        else:
            data["segments"].append(
                {
                    "id": etape.id,
                    "start": etape.start.id,
                    "to": etape.end.id,
                    "trace": [
                        (lat, lng, alt)
                        for lat, lng, alt in literal_eval(etape.trace)  # pyright: ignore[reportAny]
                    ],
                    "index": segment_index,
                }
            )
            segment_index += 1

    if len(data["stands"]) == 1 and data["stands"][0]["lat"] == 1000:
        data["stands"] = []

    return jsonify(data)


# endregion api


@set_route(parcours_bp, "/event/<event_name>/parcours/<parcours_name>")
@login_required
@admin_required
def modify_parcours(event_name: str, parcours_name: str) -> str | Response:
    event = Event.query().filter_by(name=event_name).first_or_404()
    parcours = assert404(
        event.parcours.filter_by(name=parcours_name).first()
    ).last_version
    return render_template(
        "parcours_dev.html",
        user_data=current_user,
        event_data=event,
        parcours_data=parcours,
        event_modif=True,
    )


@set_route(parcours_bp, "/event/<event_name>/parcours", methods=["POST", "GET"])
@login_required
@admin_required
def parcours_page(event_name: str) -> str | Response:
    # * page to access the differents parcours of the event
    event = Event.query().filter_by(name=event_name).first_or_404()
    user = current_user

    active_parcours = event.parcours.all()

    return render_template(
        "parcours.html",
        user_data=user,
        event_data=event,
        archived_parcours=[],
        active_parcours=active_parcours,
        event_modif=True,
    )
