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

from ast import literal_eval
from datetime import datetime
from typing import Any, TypedDict, cast
from flask_pydantic import validate

from colour import Color
from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required
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
from chrono_des_vignes.lib import (
    assert400,
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


class ParcoursDataPut(BaseModel):
    id: int
    name: str
    description: str
    creation_date: datetime
    stands: list[StandData]
    segments: list[SegmentData]
    modif: bool
    modif_allowed: bool


@api.route("/update_parcours/<int:event_id>/<int:parcours_version_id>", method="PUT")
@validate()
def update_parcours_put(body: ParcoursDataPut, event_id: int, parcours_version_id: int):
    ic("put", body.model_dump_json())
    parcours: ParcoursVersion = (
        ParcoursVersion.query()
        .filter(
            ParcoursVersion.parcours.has(Parcours.event_id == event_id),
            ParcoursVersion.id == parcours_version_id,
        )
        .first_or_404()
    )
    # metadata
    if body.id != parcours.id:
        return err("id does not correspond to the correct one")
    parcours.description = body.description
    parcours.parcours.name = body.name

    segments = sorted(body.segments, key=lambda s: s["index"])
    stands = body.stands

    # from that type of data we want to update the parcours, the stands and the segments. we will use the id field to know if we need to create a new stand/segment or update an existing one. if the id is negative it means that we need to create a new stand/segment. if the id is positive it means that we need to update an existing stand/segment with that id
    # we will first check that all the provided stands and segments are valid, then we will update/create them, and at the end we will check if there is any stand/segment that need to be deleted (if they are not in the provided data)
    # can you do it for me please ?
    errors: list[str] = []
    ids: dict[int, int] = {}  # old id to new id

    if len(segments) == 0:
        # only one stand
        if len(stands) == 0:
            # delete all segment and all stand except the start stand (set to the default one)
            Trace.query().filter_by(parcours_id=parcours_version_id).delete()
            # first select one stand and set it to default
            default_stand = assert400(
                Stand.query().filter_by(parcours_id=parcours_version_id).first()
            )
            default_stand.name = ""
            default_stand.lat = 1000
            default_stand.lng = 0
            default_stand.elevation = None
            default_stand.color = Color("#ff0000")
            default_stand.chrono = False
            Stand.query().filter_by(parcours_id=parcours_version_id).filter(
                Stand.id != default_stand.id
            ).delete()
        elif len(stands) == 1:
            Trace.query().filter_by(parcours_id=parcours_version_id).delete()
            stand_data = stands[0]
            # update the stand with the provided data and delete all the other stands
            stand = (
                Stand.query()
                .filter_by(id=stand_data["id"], parcours_id=parcours_version_id)
                .first()
            )
            if stand is None:
                return err(f"stand with id {id} do not exist")
            stand.lat = stand_data["lat"]
            stand.lng = stand_data["lng"]
            stand.name = stand_data["name"]
            try:
                stand.color = Color(stand_data["color"])
            except ValueError:
                return err(
                    f"{stand_data['color']}) is not a valid color. see https://pypi.org/project/colour/"
                )
            stand.chrono = stand_data["chrono"]
            Stand.query().filter_by(parcours_id=parcours_version_id).filter(
                Stand.id != stand.id
            ).delete()

        else:
            return err("if there is no segment there should be maximum one stand")
    else:  # there is at least one segment
        curr_index = -1
        curr_stand_id: int | None = None
        stands_ids = set[int]()
        for segment_data in segments:
            curr_index += 1
            if segment_data["index"] != curr_index:
                segment_data["index"] = curr_index
                errors.append(
                    f"segment with id {segment_data['id']} had an invalid index, it has been set to {curr_index}"
                )
            if segment_data["start"] != curr_stand_id and curr_stand_id is not None:
                # invalid start stand
                errors.append(
                    f"segment with id {segment_data['id']} had an invalid start stand id. fatal error"
                )
                return jsonify({"success": False, "errors": errors})
            curr_stand_id = segment_data["to"]
            stands_ids.add(segment_data["start"])
            stands_ids.add(segment_data["to"])
        unused_stands = set[int]()
        for stand_data in stands:
            if stand_data["id"] not in stands_ids:
                unused_stands.add(stand_data["id"])
                errors.append(
                    f"stand with id {stand_data['id']} is not used by any segment, it will be deleted"
                )
        # delete unused stands
        if len(unused_stands) > 0:
            Stand.query().filter_by(parcours_id=parcours_version_id).filter(
                Stand.id.in_(unused_stands)
            ).delete()
        # delete unused segments
        segment_ids = set[int](s["id"] for s in segments)
        Trace.query().filter_by(parcours_id=parcours_version_id).filter(
            Trace.id.not_in(segment_ids)
        ).delete()

        # update/create stands
        for stand_data in stands:
            if stand_data["id"] not in stands_ids:
                continue
            to_create = stand_data["id"] < 0
            if not to_create:
                # update the stand with the provided data
                stand = (
                    Stand.query()
                    .filter_by(id=stand_data["id"], parcours_id=parcours_version_id)
                    .first()
                )
                if stand is None:
                    errors.append(
                        f"stand with id {id} do not exist, it will be created"
                    )
                    to_create = True
                else:
                    stand.lat = stand_data["lat"]
                    stand.lng = stand_data["lng"]
                    stand.name = stand_data["name"]
                    stand.elevation = stand_data["ele"]
                    try:
                        stand.color = Color(stand_data["color"])
                    except ValueError:
                        errors.append(
                            f"{stand_data['color']}) is not a valid color. see https://pypi.org/project/colour/"
                        )
                    stand.chrono = stand_data["chrono"]
                    db.session.commit()
            if to_create:
                # create a new stand
                # check the color
                try:
                    color = Color(stand_data["color"])
                except ValueError:
                    errors.append(
                        f"{stand_data['color']}) is not a valid color. it will be set to #ff0000. see https://pypi.org/project/colour"
                    )
                    color = Color("#ff0000")
                stand = Stand(
                    name=stand_data["name"],
                    lat=stand_data["lat"],
                    lng=stand_data["lng"],
                    elevation=stand_data["ele"],
                    color=color,
                    chrono=stand_data["chrono"],
                    parcours_id=parcours_version_id,
                )
                db.session.add(stand)
                db.session.commit()
                db.session.refresh(stand)
                ids[stand_data["id"]] = stand.id

        # update/create segments
        for segment_data in segments:
            to_create = segment_data["id"] < 0
            if not to_create:
                # update the segment with the provided data
                segment = (
                    Trace.query()
                    .filter_by(id=segment_data["id"], parcours_id=parcours_version_id)
                    .first()
                )
                if segment is None:
                    errors.append(
                        f"segment with id {id} do not exist, it will be created"
                    )
                    to_create = True
                else:
                    segment.start_id = ids.get(
                        segment_data["start"], segment_data["start"]
                    )
                    segment.end_id = ids.get(segment_data["to"], segment_data["to"])
                    segment.index = segment_data["index"]

                    if (trace := Trace.check_path(segment_data["trace"])) is not None:
                        segment.path = trace
                    else:
                        errors.append(
                            f"the provided trace for segment with id {segment_data['id']} is not valid, it will be set to an empty trace"
                        )
                        segment.path = []
                    db.session.commit()
            if to_create:
                # create a new segment
                if (trace := Trace.check_path(segment_data["trace"])) is not None:
                    path = trace
                else:
                    errors.append(
                        f"the provided trace for segment with id {segment_data['id']} is not valid, it will be set to an empty trace"
                    )
                    path = []
                segment = Trace(
                    start_id=ids.get(segment_data["start"], segment_data["start"]),
                    end_id=ids.get(segment_data["to"], segment_data["to"]),
                    index=segment_data["index"],
                    name="",
                    parcours_id=parcours_version_id,
                )
                segment.path = path
                db.session.add(segment)
                db.session.commit()
                db.session.refresh(segment)
                ids[segment_data["id"]] = segment.id

    return jsonify({"success": True, "ids": ids, "errors": errors})


@api.route("/update_parcours/<int:event_id>/<int:parcours_version_id>", method="PATCH")
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
    for op in cast(list[dict[str, Any]], data):
        match op.get("op"):
            case "stand:modif":
                # Validation de l'ID et récupération de l'objet
                stand_id = get(op, "id", int)
                if stand_id is None:
                    return err("id field was not provided")

                stand = (
                    Stand.query()
                    .filter_by(id=stand_id, parcours_id=parcours.id)
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
            case "segment:modif":
                id = get(op, "id", int)
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
            case "parcours:modif":
                if (name := get(op, "name", str)) is not None:
                    parcours.parcours.name = name
                if (vesionDescription := get(op, "vesionDescription", str)) is not None:
                    parcours.description = vesionDescription
                if (description := get(op, "description", str)) is not None:
                    parcours.parcours.description = description
            case _ as o:
                return jsonify(
                    {"success": False, "error": f"op {o} is not a recognise operation"}
                )
        db.session.commit()

    return jsonify({"success": True})


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
