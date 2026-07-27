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

from datetime import datetime
from typing import Literal

from flask import Blueprint, jsonify, render_template
from flask_login import current_user
from flask_pydantic import validate
from flask_sse import sse
from pydantic import BaseModel
from werkzeug.wrappers.response import Response

from chrono_des_vignes import admin_required, db, set_route
from chrono_des_vignes.api import ApiBlueprint
from chrono_des_vignes.lib import assert404
from chrono_des_vignes.models import (
    STATUS_MAP,
    Edition,
    Event,
    Inscription,
    ParcoursVersion,
    Passage,
)

parcours = Blueprint("parcours", __name__, template_folder="templates")
run_control_api = ApiBlueprint("run_control", ["admin_required"], version="v1")


@set_route(parcours, "/event/<event_name>/editions/<edition_name>/parcours")
@admin_required
def view(event_name: str, edition_name: str) -> str | Response:
    user = current_user
    event = Event.query().filter_by(name=event_name).first_or_404()
    edition = assert404(event.editions.filter_by(name=edition_name).first())

    parcours = edition.parcours_version.first()

    return render_template(
        "edition_parcours.html",
        parcours_data=parcours,
        edition_data=edition,
        event_data=event,
        user_data=user,
        event_modif=True,
        edition_sidebar=True,
        now=datetime.now(),
    )


@run_control_api.route(
    "/get_edition_data/<int:event_id>/<int:edition_id>", method="GET"
)
def get_edition_data(event_id: int, edition_id: int):
    event = Event.query().get_or_404(event_id)
    edition = assert404(event.editions.filter_by(id=edition_id).first())

    return jsonify(edition.to_dict())


class BatchStartBody(BaseModel):
    timestamp: datetime


def start(inscription: Inscription, timestamp: datetime):
    passage = Passage(time_stamp=timestamp, inscription_id=inscription.id, key_id=None)
    db.session.add(passage)
    db.session.commit()
    db.session.refresh(passage)

    sse.publish(
        passage.SSE_data(),
        type="new_passage",
        channel=f"passages_{inscription.edition.id}_{inscription.event.id}",
    )
    sse.publish(
        passage.SSE_data(),
        type="new_passage",
        channel=f"run_control_{inscription.edition.id}_{inscription.event.id}",
    )


@run_control_api.route(
    "/launch_parcours/<int:event_id>/<int:edition_id>/<int:parcours_id>", method="POST"
)
@validate()
def api_batch_start(
    event_id: int, edition_id: int, parcours_id: int, body: BatchStartBody
):
    event = Event.query().get_or_404(event_id)
    edition = assert404(event.editions.filter_by(id=edition_id).first())
    parcours = (
        ParcoursVersion.query()
        .filter_by(id=parcours_id)
        .filter(ParcoursVersion.editions.any(Edition.id == edition.id))
        .first_or_404()
    )

    inscriptions = (
        edition.inscriptions.filter_by(parcours_id=parcours.id, present=False)
        .filter(~Inscription.passages.any())
        .all()
    )
    for inscription in inscriptions:
        start(inscription, body.timestamp)

    return jsonify({"success": True})


@run_control_api.route(
    "/parcours/<int:event_id>/<int:edition_id>/<int:parcours_id>/stop", method="POST"
)
def api_batch_stop(event_id: int, edition_id: int, parcours_id: int):
    event = Event.query().get_or_404(event_id)
    edition = assert404(event.editions.filter_by(id=edition_id).first())
    parcours = (
        ParcoursVersion.query()
        .filter_by(id=parcours_id)
        .filter(ParcoursVersion.editions.any(Edition.id == edition.id))
        .first_or_404()
    )

    inscriptions = edition.inscriptions.filter_by(
        parcours_id=parcours.id, end=None, present=False
    ).all()
    for inscription in inscriptions:
        if inscription.has_started():
            if inscription.has_finish():
                if inscription.has_all_right():
                    end = "finish"
                    status = "finished"
                else:
                    end = "disqual"
                    status = "disqualified"
            else:
                end = "abandon"
                status = "abandoned"
        else:
            end = "absent"
            status = "absent"

        inscription.end = end
        db.session.commit()
        sse.publish(
            {
                "parcoursId": inscription.parcours_id,
                "inscriptionId": inscription.id,
                "status": status,
            },
            type="status_change",
            channel=f"run_control_{inscription.edition.id}_{inscription.event.id}",
        )

    return jsonify({"success": True})


class StartBody(BaseModel):
    timestamp: datetime


@run_control_api.route(
    "/inscription/<int:event_id>/<int:edition_id>/<int:inscription_id>/start",
    method="POST",
)
@validate()
def api_start_inscription(
    event_id: int, edition_id: int, inscription_id: int, body: StartBody
):
    event = Event.query().get_or_404(event_id)
    edition = assert404(event.editions.filter_by(id=edition_id).first())

    inscription = assert404(edition.inscriptions.filter_by(id=inscription_id).first())
    start(inscription, body.timestamp)
    return jsonify({"success": None})


class action_body(BaseModel):
    status: Literal["disqualified", "abandoned", "finished"] | None

    @property
    def db_status(self):
        match self.status:
            case "disqualified":
                return "disqual"
            case "abandoned":
                return "abandon"
            case "finished":
                return "finish"
            case None:
                return None


@run_control_api.route(
    "/inscription/<int:event_id>/<int:edition_id>/<int:inscription_id>/action",
    method="POST",
)
@validate()
def api_inscription_action(
    event_id: int, edition_id: int, inscription_id: int, body: action_body
):
    event = Event.query().get_or_404(event_id)
    edition = assert404(event.editions.filter_by(id=edition_id).first())

    inscription = assert404(edition.inscriptions.filter_by(id=inscription_id).first())
    inscription.end = body.db_status
    db.session.commit()
    db.session.refresh(inscription)

    sse.publish(
        {
            "parcoursId": inscription.parcours_id,
            "inscriptionId": inscription.id,
            "status": STATUS_MAP[inscription.status],
        },
        type="status_change",
        channel=f"run_control_{inscription.edition.id}_{inscription.event.id}",
    )
    return jsonify({"success": True})
