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
from typing import TypedDict, cast

from flask import Blueprint, flash, jsonify, redirect, render_template
from flask_login import current_user, login_required
from sqlalchemy import or_
from werkzeug.wrappers import Response

from chrono_des_vignes import admin_required, db, set_route
from chrono_des_vignes import lang_url_for as url_for
from chrono_des_vignes.admin.editions.form import Edition_form
from chrono_des_vignes.api import ApiBlueprint
from chrono_des_vignes.lib import assert400, assert404
from chrono_des_vignes.models import Edition, Event, Parcours, ParcoursVersion, Stand

from .dossard import dossard
from .parcours import parcours
from .passages import passages
from .result import result

editions = Blueprint("editions", __name__, template_folder="templates")
editions.register_blueprint(dossard)
editions.register_blueprint(passages)
editions.register_blueprint(parcours)
editions.register_blueprint(result)

edition_api = ApiBlueprint.admin("edition", version="v1")


class StandData(TypedDict):
    name: str
    lat: float
    lng: float
    id: int


class ParcoursData(TypedDict):
    name: str
    description: str
    chrono_stands: list[StandData]


class EditionData(TypedDict):
    name: str
    edition_date: datetime
    description: str
    first_inscription: datetime
    last_inscription: datetime
    rdv_lat: float
    rdv_lng: float
    parcours: list[ParcoursData]


@edition_api.route("get_edition/<event_id>/<edition_id>")
def get_edition(event_id: int, edition_id: int):
    event = Event.query().filter_by(id=event_id).first_or_404()
    edition = assert404(event.editions.filter_by(id=edition_id).first())
    data = EditionData(
        name=edition.name,
        edition_date=edition.edition_date,
        description=edition.description,
        first_inscription=edition.first_inscription,
        last_inscription=edition.last_inscription,
        rdv_lat=edition.rdv_lat,
        rdv_lng=edition.rdv_lng,
        parcours=[],
    )

    for pv in edition.parcours_version:
        parcours_data = ParcoursData(
            name=pv.parcours.name, description=pv.parcours.description, chrono_stands=[]
        )
        for cs in pv.stands.filter(Stand.chrono.is_(True)).all():
            stand_data = StandData(name=cs.name, lat=cs.lat, lng=cs.lng, id=cs.id)
            parcours_data["chrono_stands"].append(stand_data)
        data["parcours"].append(parcours_data)

    return jsonify(data)


@set_route(editions, "/event/<event_name>/editions", methods=["POST", "GET"])
@login_required
@admin_required
def editions_page(event_name: str) -> str | Response:
    # * page to access the differents editions of the event
    event = Event.query().filter_by(name=event_name).first_or_404()
    user = current_user
    form = Edition_form()
    form.parcours.choices = [str((e.name, e.description)) for e in event.parcours.all()]  # type: ignore
    if form.validate_on_submit():
        if not event.editions.filter_by(name=form.name.data).first():
            # ok nom pas utilisé
            parcours_id = [
                cast(int, eval(p)[0])
                for p in cast(list[str], (assert400(form.parcours.data)))
            ]  # type: ignore[union-attr]
            parcours = [
                p.last_version
                for p in event.parcours.filter(Parcours.name.in_(parcours_id)).all()
            ]
            edition = Edition(
                name=form.name.data,
                event_id=event.id,
                edition_date=form.edition_date.data,
                description=form.description.data,
                first_inscription=form.first_inscription.data,
                last_inscription=form.last_inscription.data,
                rdv_lat=form.rdv_lat.data,
                rdv_lng=form.rdv_lng.data,
            )
            edition.parcours_version = parcours
            db.session.add(edition)
            db.session.commit()
            flash("edition bien crée", "success")
            return redirect(
                url_for("admin.editions.editions_page", event_name=event.name)
            )
        else:
            form.name.errors = list(form.name.errors) + ["vous utiliser deja ce nom."]

    return render_template(
        "editions.html", user_data=user, event_data=event, form=form, event_modif=True
    )


@set_route(
    editions,
    "/event/<event_name>/editions/<edition_name>/delete",
    methods=["POST", "GET"],
)
@login_required
@admin_required
def delete_edition_page(event_name: str, edition_name: str) -> str | Response:
    event = Event.query().filter_by(name=event_name).first_or_404()
    edition = assert404(event.editions.filter_by(name=edition_name).first())
    if edition.first_inscription <= datetime.now():
        flash(
            "l'edition ne peut pas être supprimée car les inscriptions sont déjà ouvertes",
            "danger",
        )
        return redirect(
            url_for(
                "admin.editions.modify_edition_page",
                event_name=event.name,
                edition_name=edition.name,
            )
        )
    elif edition.passage_keys.count() > 0:
        flash(
            "l'edition ne peut pas être supprimée car des passages keys existent",
            "danger",
        )
        return redirect(
            url_for(
                "admin.editions.modify_edition_page",
                event_name=event.name,
                edition_name=edition.name,
            )
        )

    db.session.delete(edition)
    db.session.commit()
    flash("l'edition a bien été supprimée", "success")
    return redirect(url_for("admin.editions.editions_page", event_name=event.name))


@set_route(
    editions, "/event/<event_name>/editions/<edition_name>", methods=["POST", "GET"]
)
@login_required
@admin_required
def modify_edition_page(event_name: str, edition_name: str) -> str | Response:
    event = Event.query().filter_by(name=event_name).first_or_404()
    edition = assert404(event.editions.filter_by(name=edition_name).first())
    user = current_user
    form = Edition_form(
        data={
            "name": edition.name,
            "edition_date": edition.edition_date,
            "description": edition.description,
            "first_inscription": edition.first_inscription,
            "last_inscription": edition.last_inscription,
            "rdv_lat": edition.rdv_lat,
            "rdv_lng": edition.rdv_lng,
            "parcours": [
                str((p.name, p.parcours.description)) for p in edition.parcours_version
            ],
        }
    )
    form.parcours.choices = [
        str((p.name, p.description))
        for p in event.parcours.filter(
            Parcours.versions.any(
                or_(
                    ParcoursVersion.archived.is_(False),
                    ParcoursVersion.editions.any(Edition.id == edition.id),
                )
            )
        ).all()
    ]

    # ? desactiver le champs si dates deja passé
    form.edition_date.render_kw.pop("disabled", None)
    form.first_inscription.render_kw.pop("disabled", None)
    form.last_inscription.render_kw.pop("disabled", None)
    form.name.render_kw = {}
    form.rdv_lat.render_kw = {}
    form.rdv_lng.render_kw = {}
    form.parcours.render_kw = {}
    if edition.first_inscription <= datetime.now():
        # si ils peuvent s'iscrire ne plus modifier la date de l'edition
        form.edition_date.render_kw["disabled"] = "disabled"
        form.parcours.render_kw["disabled"] = "disabled"
        form.parcours.data = [
            str((p.name, p.parcours.description)) for p in edition.parcours_version
        ]
        form.first_inscription.render_kw["disabled"] = "disabled"
        form.name.render_kw["disabled"] = "disabled"
        form.rdv_lat.render_kw["disabled"] = "disabled"
        form.rdv_lng.render_kw["disabled"] = "disabled"
    if edition.last_inscription <= datetime.now():
        form.last_inscription.render_kw["disabled"] = "disabled"
    # ? fin desactivation des champs

    if form.validate_on_submit():
        # ic(edition.rdv_lat, form.rdv_lat.data, edition.rdv_lng, form.rdv_lng.data)
        if (
            form.name.data == edition.name
            or not event.editions.filter_by(name=form.name.data).first()
        ):
            edition.name = form.name.data
            edition.edition_date = form.edition_date.data
            edition.description = form.description.data
            edition.parcours_version = [
                p.last_version
                for p in event.parcours.filter(
                    Parcours.name.in_(
                        [eval(p)[0] for p in assert400(form.parcours.data)]
                    )
                ).all()
            ]  # type: ignore[union-attr]
            edition.first_inscription = form.first_inscription.data
            edition.last_inscription = form.last_inscription.data
            edition.rdv_lat = form.rdv_lat.data
            edition.rdv_lng = form.rdv_lng.data
            db.session.commit()
            flash("l'edition a bien été mise a jour.", "success")
            return redirect(
                url_for("admin.editions.editions_page", event_name=event.name)
            )
        else:
            form.name.errors = list(form.name.errors) + ["vous utiliser deja ce nom."]
    return render_template(
        "modify_edition.html",
        user_data=user,
        event_data=event,
        edition_data=edition,
        form=form,
        now=datetime.now(),
        event_modif=True,
        edition_sidebar=True,
    )
