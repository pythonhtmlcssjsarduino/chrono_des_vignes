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

from flask import Blueprint, flash, redirect, render_template
from flask_babel import _
from flask_login import current_user, login_required
from werkzeug.wrappers import Response

from chrono_des_vignes import db, set_route
from chrono_des_vignes import lang_url_for as url_for
from chrono_des_vignes.lib import assert404, create_gcalendar_link, deg_to_dms
from chrono_des_vignes.models import Event, Inscription

view = Blueprint("view", __name__, template_folder="templates")


@set_route(view, "/view/inscription/<inscription_id>/delete")
@login_required
def delete_inscription(inscription_id: str) -> str | Response:
    user = current_user
    inscription: Inscription = assert404(
        user.inscriptions.filter_by(id=inscription_id).first(),
        _("view.error.notyourinscription"),
    )
    if (
        inscription.edition.edition_date < datetime.now()
        or inscription.passages.count() > 0
    ):
        return redirect(
            url_for("view.view_inscription_page", inscription_id=inscription.id)
        )
    if inscription.data and inscription.data.inscriptions.count() == 1:
        db.session.delete(inscription.data)
    db.session.delete(inscription)
    db.session.commit()

    return redirect(url_for("home"))


@set_route(view, "/view/inscription/<inscription_id>")
@login_required
def view_inscription_page(inscription_id: str) -> str | Response:
    user = current_user
    inscription = assert404(Inscription.query().filter_by(id=inscription_id).first())
    edition = inscription.edition
    if inscription.inscrit.id != user.id and inscription.event.createur.id != user.id:
        flash(_("view.error.notyourinscription"), "warning")
        return redirect(url_for("home"))

    rdv_url = (
        "https://www.google.com/maps/place/{0}%C2%B0{1}'{2}".format(
            *deg_to_dms(edition.rdv_lat)
        )
        + "%22N+{0}%C2%B0{1}'{2}".format(*deg_to_dms(edition.rdv_lng))
        + f"%22E/@{edition.rdv_lat},{edition.rdv_lng},15z"
    )

    return render_template(
        "view_inscription.html",
        user_data=user,
        inscription=inscription,
        rdv_url=rdv_url,
    )


@set_route(view, "/view/<event>")
def view_event_page(event: str) -> str | Response:
    user_data = current_user if current_user.is_authenticated else None
    event_ = assert404(
        Event.query().filter_by(name=event).first(),
        _("view.error.eventdontexist:event").format(event=event),
    )
    return render_template(
        "view_event.html", user_data=user_data, event_data=event_, time=datetime.now()
    )


@set_route(view, "/view/<event_name>/edition/<edition_name>")
def view_edition_page(event_name: str, edition_name: str) -> str | Response:
    user = current_user if current_user.is_authenticated else None
    event = (
        Event.query()
        .filter_by(name=event_name)
        .first_or_404(_("view.error.eventdontexist:event").format(event=event_name))
    )
    edition = assert404(
        event.editions.filter_by(name=edition_name).first(),
        _("view.error.editiondontexist:edition").format(edition=edition_name),
    )

    rdv_url = (
        "https://www.google.com/maps/place/{0}%C2%B0{1}'{2}".format(
            *deg_to_dms(edition.rdv_lat)
        )
        + "%22N+{0}%C2%B0{1}'{2}".format(*deg_to_dms(edition.rdv_lng))
        + f"%22E/@{edition.rdv_lat},{edition.rdv_lng},15z"
    )
    gcalendar_url = create_gcalendar_link(
        f"{event.name} {_('view.edition')} {edition.name}",
        edition.edition_date,
        edition.edition_date,
    )
    return render_template(
        "view_edition.html",
        user_data=user,
        event_data=event,
        edition_data=edition,
        rdv_url=rdv_url,
        gcalendar_url=gcalendar_url,
        time=datetime.now(),
    )

@set_route(view, "/view/<event_name>/parcours/<parcours_name>")
def view_parcours_page(event_name: str, parcours_name: str) -> str | Response:
    user_data = current_user if current_user.is_authenticated else None
    event = (
        Event.query()
        .filter_by(name=event_name)
        .first_or_404(_("view.error.eventdontexist:event").format(event=event_name))
    )
    parcours = assert404(
        event.parcours.filter_by(name=parcours_name).first(),
        _("view.error.parcoursdontexist:parcours").format(parcours=parcours_name),
    )

    return render_template(
        "view_parcours.html", user_data=user_data, parcours=parcours, event_data=event
    )
