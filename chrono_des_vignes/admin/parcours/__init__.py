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
from flask import Blueprint, flash, jsonify, redirect, render_template, request, abort
from icecream import ic
from chrono_des_vignes import admin_required, db, set_route, lang_url_for as url_for
from chrono_des_vignes.api import ApiBlueprint
from .form import (
    Parcours_name_form,
    Etape_modif_form,
    Stand_modif_form,
    New_parcours_form,
)
from flask_login import login_required, current_user
from chrono_des_vignes.models import (
    Event,
    Parcours,
    Stand,
    Trace,
    ParcoursVersion,
    get_column_max_length,
)
from folium import Map, Marker, Icon, PolyLine, Popup, LayerControl, TileLayer
from folium.template import Template
from colour import Color
from chrono_des_vignes.lib import (
    assert400,
    assert404,
    get_points_elevation,
    calc_points_dist,
    midpoint,
    is_valide_name,
)
from sqlalchemy import or_
from werkzeug.wrappers.response import Response
from flask_wtf import FlaskForm
from typing import Any, Literal, TypedDict, cast

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
    data = request.get_data().decode()
    name = data.split("&")[0].split("=")[1]
    if not is_valide_name(name, get_column_max_length(Parcours, "name"), 0):
        flash("invalide name :", "warning")
        return redirect(
            url_for(
                "admin.parcours.parcours_page",
                event_name=Event.query().filter_by(id=event_id).first_or_404().name,
            )
        )

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
    return redirect(
        url_for(
            "admin.parcours.dev_parcours_page",
            event_name=Event.query().filter_by(id=event_id).first_or_404().name,
            parcours_name=parcours.name,
        )
    )


# region

# endregion


@api.route("/update_parcours/<int:event_id>/<int:parcours_version_id>", method="POST")
def update_parcours(event_id: int, parcours_version_id: int):
    parcours = (
        ParcoursVersion.query()
        .filter(
            ParcoursVersion.parcours.has(Parcours.event_id == event_id),
            ParcoursVersion.id == parcours_version_id,
        )
        .first_or_404()
    )
    data: Any = request.get_json()  # pyright: ignore[reportAny]

    if not isinstance(data, list):
        return jsonify({"success": False, "error": "data not valid not a list"})

    for op in data:
        print(op)

    return jsonify({"success": True, "ids": {}})


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


@set_route(parcours_bp, "/event/<event_name>/parcours/<parcours_name>/dev")
@login_required
@admin_required
def dev_parcours_page(event_name: str, parcours_name: str) -> str | Response:
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


# endregion api


# region old #############
@set_route(parcours_bp, "/event/<event_name>/parcours/<parcours_name>/delete")
@login_required
@admin_required
def delete_parcours_page(event_name: str, parcours_name: str) -> str | Response:
    event = Event.query().filter_by(name=event_name).first_or_404()
    parcours = assert404(event.parcours.filter_by(name=parcours_name).first())
    if parcours.editions.count() > 0:
        flash(
            "action impossible le parcours est déjà utilisé dans une edition.", "danger"
        )
        return redirect(
            url_for(
                "admin.parcours.modify_parcours",
                event_name=event.name,
                parcours_name=parcours.name,
                force_modif=request.args.get("force_modif", None),
            )
        )
    for e in tuple(parcours):
        db.session.delete(e)
    db.session.delete(parcours)
    db.session.commit()
    flash("parcours supprimé!", "success")

    return redirect(url_for("admin.parcours.parcours_page", event_name=event.name))


@set_route(parcours_bp, "/event/<event_name>/parcours/<parcours_name>/copy")
@login_required
@admin_required
def copy_parcours(event_name: str, parcours_name: str) -> str | Response:
    event = Event.query().filter_by(name=event_name).first_or_404()
    parcours = assert404(event.parcours.filter_by(name=parcours_name).first())

    p = ParcoursVersion(
        name=f"{parcours.name} copy",
        event_id=event.id,
        description=parcours.description,
        chronos_list=parcours.chronos_list,
    )
    db.session.add(p)
    db.session.commit()
    db.session.refresh(p)
    old_stands = Stand.query().filter_by(parcours_id=parcours.id).all()
    old_to_new_id: dict[int, int] = {}
    for old_stand in old_stands:
        new_stand = Stand(
            name=old_stand.name,
            lat=old_stand.lat,
            lng=old_stand.lng,
            elevation=old_stand.elevation,
            parcours_id=p.id,
            start_stand=p.id if old_stand.start_stand else None,
            end_stand=p.id if old_stand.end_stand else None,
            color=old_stand.color,
            chrono=old_stand.chrono,
        )
        db.session.add(new_stand)
        db.session.commit()
        db.session.refresh(new_stand)
        old_to_new_id[old_stand.id] = new_stand.id

    old_traces: list[Trace] = Trace.query().filter_by(parcours_id=parcours.id).all()
    for old_trace in old_traces:
        new_trace = Trace(
            name=old_trace.name,
            parcours_id=p.id,
            start_id=old_to_new_id[old_trace.start_id],
            end_id=old_to_new_id[old_trace.end_id],
            trace=old_trace.trace,
            turn_nb=old_trace.turn_nb,
        )
        db.session.add(new_trace)
        db.session.commit()

    return redirect(
        url_for(
            "admin.parcours.modify_parcours",
            event_name=event.name,
            parcours_name=f"{parcours.name} copy",
        )
    )


@set_route(parcours_bp, "/event/<event_name>/parcours/<parcours_name>/archive")
@login_required
@admin_required
def archive_parcours_page(event_name: str, parcours_name: str) -> str | Response:
    event = Event.query().filter_by(name=event_name).first_or_404()
    parcours = assert404(event.parcours.filter_by(name=parcours_name).first())
    parcours.archived = True
    db.session.commit()
    return redirect(url_for("admin.parcours.parcours_page", event_name=event.name))


@set_route(parcours_bp, "/event/<event_name>/parcours/<parcours_name>/unarchive")
@login_required
@admin_required
def unarchive_parcours_page(event_name: str, parcours_name: str) -> str | Response:
    event = Event.query().filter_by(name=event_name).first_or_404()
    parcours = assert404(event.parcours.filter_by(name=parcours_name).first())
    parcours.archived = False
    db.session.commit()
    return redirect(url_for("admin.parcours.parcours_page", event_name=event.name))


@set_route(parcours_bp, "/event/<event_name>/parcours", methods=["POST", "GET"])
@login_required
@admin_required
def parcours_page(event_name: str) -> str | Response:
    # * page to access the differents parcours of the event
    event = Event.query().filter_by(name=event_name).first_or_404()
    user = current_user

    form = New_parcours_form()
    if form.validate_on_submit():
        if not event.parcours.filter_by(name=form.name.data).first():
            # ok nom pas utilisé

            p = ParcoursVersion(name=assert400(form.name.data), event_id=event.id)
            db.session.add(p)
            db.session.commit()
            db.session.refresh(p)
            s = Stand(
                name=f"debut-{form.name.data}"[:36],
                parcours_id=p.id,
                lat=assert400(form.start_lat.data),
                lng=assert400(form.start_lng.data),
                chrono=True,
                start_stand=p.id,
                end_stand=p.id,
                elevation=None,
            )
            db.session.add(s)
            db.session.commit()

            return redirect(
                url_for(
                    "admin.parcours.modify_parcours",
                    event_name=event.name,
                    parcours_name=form.name.data,
                    force_modif=request.args.get("force_modif", None),
                )
            )
        else:
            form.name.errors = list(form.name.errors) + ["vous utiliser deja ce nom."]
    active_parcours = event.parcours.all()

    return render_template(
        "parcours.html",
        user_data=user,
        event_data=event,
        archived_parcours=[],
        active_parcours=active_parcours,
        event_modif=True,
        form=form,
    )


def build_alt_graph(graph_data: list[Stand | Trace]) -> Any | None:
    return None

    points = []  # pyright: ignore[reportUnreachable]
    to_request = []
    last_point = None
    dist = 0
    for e in graph_data:
        if isinstance(e, Stand):
            dist += (
                calc_points_dist(e.lat, e.lng, last_point[0], last_point[1])
                if last_point
                else 0
            )
            last_point = e.lat, e.lng
            if e.elevation:
                points.append(
                    {"x": dist, "y": e.elevation, "label": e.name, "type": "stand"}
                )
            else:
                to_request.append(e)
                points.append({"x": dist, "y": 0, "label": e.name, "type": "stand"})
        elif isinstance(e, Trace):
            trace = e
            if len(trace):
                if trace.has_alt():  # si il y a l'altitude
                    for point in trace:
                        dist += calc_points_dist(
                            point.lat, point.lng, last_point[0], last_point[1]
                        )
                        last_point = point.lat, point.lng
                        points.append(
                            {
                                "x": dist,
                                "y": point.alt,
                                "label": e.name,
                                "type": "trace",
                            }
                        )
                else:
                    response = get_points_elevation(
                        [(lat, lng) for lat, lng, _ in trace]
                    )
                    if response is not None:
                        e.set_trace(
                            [
                                (p["latitude"], p["longitude"], p["elevation"])
                                for p in response
                            ]
                        )
                        db.session.commit()
                        for point in trace:
                            dist += calc_points_dist(
                                point.lat, point.lng, last_point[0], last_point[1]
                            )
                            last_point = point.lat, point.lng
                            points.append(
                                {
                                    "x": dist,
                                    "y": point.alt,
                                    "label": e.name,
                                    "type": "trace",
                                }
                            )

    response = get_points_elevation([(req.lat, req.lng) for req in to_request])
    if len(to_request) > 0 and response is not None:
        for index, point in enumerate(points):
            if point["y"] is None:
                ele = response.pop(0)["elevation"]
                to_request.pop(0).elevation = ele
                points[index]["y"] = ele
        db.session.commit()

    return points


class MarkerDict(TypedDict):
    lat: float
    lng: float
    name: str


class TraceItem(TypedDict):
    type: Literal["trace"]
    name: str
    id: int
    trace: list[tuple[float, float]]  # assuming it's a list of coordinates


class MarkerItem(TypedDict):
    type: Literal["marker"]
    lat: float
    lng: float
    name: str
    id: int
    color: str
    step: int


def make_popup(callback: str):
    popup = Popup()
    template = (
        """  
                var {{this.get_name()}} = L.popup({{ this.options|tojson }});
                {{ this._parent.get_name() }}.on("click", function() {%s})
                """
        % callback
    )
    popup._template = Template(template)  # pyright: ignore[reportPrivateUsage]
    return popup


def create_map_and_alt_graph(
    parcours: ParcoursVersion,
    modif: bool = False,
    rdv: tuple[float, float] | None = None,
    current_stand_id: int | None = None,
    current_trace_id: str | None = None,
):
    #! create the map
    map_style = request.args.get("map", "osm")
    map_styles: dict[str, dict[str, str | int | None]] = {
        "topo": {
            "tiles": "https://tile.opentopomap.org/{z}/{x}/{y}.png",
            "attr": "opentopomap",
            "name": "topographie",
            "max_zoom": 17,
        },
        "sat": {
            "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            "attr": "Esri",
            "name": "Satellite",
            "max_zoom": 20,
        },
        "osm": {"tiles": "OpenStreetMap", "attr": None, "name": None, "max_zoom": 20},
    }
    map_styles = {
        k: v if k == map_style else {**v, "show": False} for k, v in map_styles.items()
    }

    program_list: list[TraceItem | MarkerItem] = []
    part_list: list[Stand | Trace] = []
    marker_coordonee: list[tuple[float, float]] = []
    stands = set[int]()
    next_path_name: list[str] = []
    last_path_name: list[str] = []
    markers_name: list[MarkerDict] = []
    chrono_list: list[int] = []
    start = parcours.start_stand
    map = Map(max_zoom=22, location=(0, 0), zoom_start=1)
    new_stand: Stand = start
    # si aucun depart alors ne mettre aucun stand
    if start:
        if modif:
            popup = make_popup("on_marker_click(%s)" % start.id)
        else:
            popup = None
        last_m: Marker = Marker(
            (start.lat, start.lng),
            tooltip=start.name,
            icon=Icon(
                icon_color=start.color.get_hex(),
                icon="flag-checkered",
                prefix="fa",
                color="orange" if new_stand.id != current_stand_id else "green",
            ),
            popup=popup,
        )
        last_m.add_to(map)
        element_name = last_m.get_name()
        part_list.append(start)
        program_list.append(
            {
                "type": "marker",
                "lat": start.lat,
                "lng": start.lng,
                "name": start.name,
                "id": start.id,
                "color": start.color.get_hex(),
                "step": 0,
            }
        )
        stands.add(start.id)
        chrono_list.append(start.id)
        turn_nb = 0
        step = 0
        while True:
            if new_stand == start:
                turn_nb += 1
            step += 1
            old_stand = new_stand
            # si l'ancien stand a une trace qui part de lui
            trace = old_stand.start_trace.filter_by(turn_nb=turn_nb).first()
            if trace is not None:
                new_stand = trace.end
                if new_stand.chrono:
                    chrono_list.append(new_stand.id)
                if new_stand.id not in stands:
                    if modif:
                        popup = make_popup("on_marker_click(%s)" % new_stand.id)
                        popup = None
                    last_m = Marker(
                        (new_stand.lat, new_stand.lng),
                        tooltip=new_stand.name,
                        icon=Icon(
                            icon_color=new_stand.color.get_hex(),
                            prefix="fa",
                            icon="stopwatch" if new_stand.chrono else "circle-info",
                        ),
                        popup=popup if modif else None,
                    )
                    last_m.add_to(map)
                    if (
                        current_stand_id is not None
                        and new_stand.id == current_stand_id
                    ):
                        last_m.icon.options["markerColor"] = "green"  # pyright: ignore[reportUnknownMemberType]
                        element_name = last_m.get_name()

                    # plus pour savoir si le stand est deja sur la map et la mettre sur la liste des programme
                    stands.add(new_stand.id)

                part_list.append(trace)
                part_list.append(new_stand)

                program_list.append(
                    {
                        "type": "trace",
                        "name": trace.name,
                        "id": trace.id,
                        "trace": eval(trace.trace),
                    }
                )
                program_list.append(
                    {
                        "type": "marker",
                        "lat": new_stand.lat,
                        "lng": new_stand.lng,
                        "name": new_stand.name,
                        "id": new_stand.id,
                        "color": new_stand.color.get_hex(),
                        "step": step,
                    }
                )

                poly_points = [
                    (old_stand.lat, old_stand.lng),
                    *(
                        (lat, lng)
                        for lat, lng, _ in cast(
                            list[tuple[float, float, float]], literal_eval(trace.trace)
                        )
                    ),
                    (new_stand.lat, new_stand.lng),
                ]
                marker_coordonee += poly_points
                if modif:
                    popup = make_popup("on_trace_click(%s)" % trace.id)
                if str(trace.id) != current_trace_id:
                    poly = PolyLine(
                        poly_points, tooltip=trace.name, popup=popup if modif else None
                    ).add_to(map)  # type: ignore
                if current_stand_id is not None and new_stand.id == current_stand_id:
                    last_path_name.append(poly.get_name())  # pyright: ignore[reportPossiblyUnboundVariable]
                elif current_stand_id is not None and old_stand.id == current_stand_id:
                    next_path_name.append(poly.get_name())  # pyright: ignore[reportPossiblyUnboundVariable]
            else:
                last_m.icon.options["icon"] = "flag-checkered"  # pyright: ignore[reportUnknownMemberType]
                last_m.icon.options["prefix"] = "fa"  # pyright: ignore[reportUnknownMemberType]
                break
    else:
        element_name = None

    parcours.chronos_list = str(chrono_list)
    db.session.commit()

    graph = build_alt_graph(part_list)

    # afficher le trace pour les modifications
    if current_trace_id is not None and modif:
        trace = Trace.query().filter_by(id=current_trace_id).first()
        if trace is None or trace.parcours != parcours:
            abort(400)
        points: list[tuple[float, float]] = [
            (trace.start.lat, trace.start.lng),
            *[
                (lat, lng)
                for lat, lng, _ in cast(
                    list[tuple[float, float, float]], literal_eval(trace.trace)
                )
            ],
            (trace.end.lat, trace.end.lng),
        ]
        marker_coordonee += points
        popup = make_popup("on_trace_click(%s)" % trace.id)
        line = PolyLine(points, dash_array="5", tooltip=trace.name, popup=popup).add_to(
            map
        )  # type: ignore
        element_name = line.get_name()
        last_point: tuple[float, float] = points[0]
        i = -1
        for i, (lat, lng) in enumerate(
            points[1:-1]
        ):  # affiche chaque marker d'angle et les signes plus pour ajouter un point
            popup = make_popup("trace_point_modif(%s)" % f"{lat}, {lng}")
            # place le marker a l'angle
            marker = Marker(
                (lat, lng),
                icon=Icon(icon="flag", prefix="fa", color="green"),
                popup=popup,
            ).add_to(map)

            # affiche le plus pour ajouter un point sur
            # le point central entre les deux points
            midlatlng = midpoint(last_point, (lat, lng))
            popup = make_popup(
                "trace_point_add(%s)" % f"{midlatlng[0]}, {midlatlng[1]}, {i}"
            )
            Marker(
                (midlatlng[0], midlatlng[1]),
                popup=popup,
                icon=Icon(icon="circle-plus", prefix="fa", color="lightgreen"),
            ).add_to(map)
            ####
            markers_name.append({"lat": lat, "lng": lng, "name": marker.get_name()})
            last_point = (lat, lng)
        # affiche le dernier point d'ajout
        midlatlng = midpoint(last_point, points[-1])
        popup = make_popup(
            "trace_point_add(%s)" % f"{midlatlng[0]}, {midlatlng[1]}, {i + 1}"
        )
        Marker(
            (midlatlng[0], midlatlng[1]),
            popup=popup,
            icon=Icon(icon="circle-plus", prefix="fa", color="lightgreen"),
        ).add_to(map)

    # trouver et centre la map sur le parcours
    lats, lngs = (
        set([i[0] for i in marker_coordonee]),
        set([i[1] for i in marker_coordonee]),
    )
    marker_coordonee = [(la, lo) for la, lo in marker_coordonee]
    if len(lats) != 0 or len(lngs) != 0:
        map.fit_bounds([min(marker_coordonee), max(marker_coordonee)], max_zoom=19)
    # ? ajout different layer
    # TileLayer('OpenStreetMap', max_zoom=20).add_to(map)
    # TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='satelite', max_zoom=20).add_to(map)
    for _, data in map_styles.items():
        TileLayer(**data).add_to(map)  # type: ignore  # pyright: ignore[reportArgumentType]
    LayerControl().add_to(map)

    if rdv:
        lat, lng = rdv
        Marker(
            (lat, lng),
            tooltip="rendez-vous",
            icon=Icon(
                icon_color="#0f0", prefix="fa", icon="arrows-to-circle", color="red"
            ),
        ).add_to(map)
        map.fit_bounds([(lat, lng), (lat, lng)], max_zoom=15)

    return (
        element_name,
        last_path_name,
        next_path_name,
        markers_name,
        program_list,
        map,
        graph,
    )


@set_route(
    parcours_bp, "/event/<event_name>/parcours/<parcours_name>", methods=["POST", "GET"]
)
@login_required
@admin_required
def modify_parcours(event_name: str, parcours_name: str) -> str | Response:
    event = Event.query().filter_by(name=event_name).first_or_404()
    parcours = assert404(event.parcours.filter_by(name=parcours_name).first())

    return render_modify_parcours(event, parcours)


@set_route(
    parcours_bp,
    "/event/<event_name>/parcours/<parcours_name>/stand/<int:stand_id>",
    methods=["POST", "GET"],
)
@login_required
@admin_required
def modify_stand(event_name: str, parcours_name: str, stand_id: int) -> str | Response:
    event = Event.query().filter_by(name=event_name).first_or_404()
    parcours = assert404(event.parcours.filter_by(name=parcours_name).first())
    stand = parcours.stands.filter_by(id=stand_id).first()

    if stand is None:
        return redirect(
            url_for(
                "parcours.modify_parcours",
                event_name=event.name,
                parcours_name=parcours.name,
                force_modif=request.args.get("force_modif", None),
            )
        )
    first_or_last = parcours.end_stand == stand or parcours.start_stand == stand

    modif_form = Stand_modif_form(
        data={
            "name": stand.name,
            "lat": stand.lat,
            "lng": stand.lng,
            "color": stand.color.get_hex_l(),
            "chrono": stand.chrono,
        }
    )

    if first_or_last:
        modif_form.chrono.render_kw = {"disabled": ""}

    if modif_form.validate_on_submit():
        if (
            stand.name == modif_form.name.data
            or not parcours.stands.filter_by(name=modif_form.name.data).first()
        ):
            # name
            stand.name = assert400(modif_form.name.data)
            if stand.lat != modif_form.lat.data or stand.lng != modif_form.lng.data:
                # lat
                stand.lat = assert400(modif_form.lat.data)
                # lng
                stand.lng = assert400(modif_form.lng.data)
                # elevation
                ele = get_points_elevation(
                    [(assert400(modif_form.lat.data), assert400(modif_form.lng.data))]
                )  # type: ignore
                if ele:
                    stand.elevation = ele[0]["elevation"]
            # color
            stand.color = Color(modif_form.color.data)
            # chrono
            stand.chrono = bool(modif_form.chrono.data)
            db.session.commit()
            return redirect(
                url_for(
                    "admin.parcours.modify_parcours",
                    event_name=event.name,
                    parcours_name=parcours.name,
                    force_modif=request.args.get("force_modif", None),
                )
            )
        else:
            modif_form.name.errors = list(modif_form.name.errors) + [
                "vous utiliser déjà ce nom."
            ]

    return render_modify_parcours(event, parcours, "marker", modif_form, stand=stand)


@set_route(
    parcours_bp,
    "/event/<event_name>/parcours/<parcours_name>/trace/<int:trace_id>",
    methods=["POST", "GET"],
)
@login_required
@admin_required
def modify_trace(event_name: str, parcours_name: str, trace_id: int) -> str | Response:
    event = Event.query().filter_by(name=event_name).first_or_404()
    parcours = assert404(event.parcours.filter_by(name=parcours_name).first())
    trace = parcours.traces.filter_by(id=trace_id).first()

    if trace is None:
        return redirect(
            url_for(
                "parcours.modify_parcours",
                event_name=event.name,
                parcours_name=parcours.name,
                force_modif=request.args.get("force_modif", None),
            )
        )

    #! creation du formulaire de modification
    modif_form = Etape_modif_form(
        data={
            "name": trace.name,
            "path": str(
                [
                    [lat, lng]
                    for lat, lng, _ in cast(
                        list[tuple[float, float, float]], literal_eval(trace.trace)
                    )
                ]
            ),
        }
    )
    if modif_form.validate_on_submit():
        if (
            trace.name == modif_form.name.data
            or not parcours.traces.filter_by(name=modif_form.name.data).first()
        ):
            # name
            trace.name = assert400(modif_form.name.data)
            try:

                def float_int(value: str | int | float) -> float | int:
                    try:
                        str(value).index(".")
                        return float(value)
                    except (ValueError, TypeError):
                        return int(value)

                path = cast(
                    list[tuple[float, float]],
                    literal_eval(assert400(modif_form.path.data)),
                )
                new = [(float_int(lat), float_int(lng)) for lat, lng in path]
                elevation = get_points_elevation(new)
                new_trace = str(
                    [
                        [float_int(lat), float_int(lng), float_int(ele["elevation"])]
                        for (lat, lng), ele in zip(path, elevation)
                    ]
                )  # type: ignore
            except Exception:
                return redirect(
                    url_for(
                        "admin.parcours.modify_parcours",
                        event_name=event.name,
                        parcours_name=parcours.name,
                        force_modif=request.args.get("force_modif", None),
                    )
                )
            else:
                trace.trace = new_trace
            db.session.commit()
            # return redirect(request.path)
        else:
            modif_form.name.errors = list(modif_form.name.errors) + [
                "vous utiliser deja ce nom."
            ]

    return render_modify_parcours(event, parcours, "trace", modif_form, trace=trace)


@set_route(
    parcours_bp,
    "/event/<event_name>/parcours/<parcours_name>/new/<int:last_marker>",
    methods=["POST", "GET"],
)
@login_required
@admin_required
def new_stand(event_name: str, parcours_name: str, last_marker: int) -> str | Response:
    event = Event.query().filter_by(name=event_name).first_or_404()
    parcours = assert404(event.parcours.filter_by(name=parcours_name).first())

    # trouve le marker qui est le debut de la traces
    turn_nb = 1
    stand: Stand = parcours.start_stand
    for _ in range(last_marker):
        stand = assert400(stand.start_trace.filter_by(turn_nb=turn_nb).first()).end
        if stand == parcours.start_stand:
            turn_nb += 1
    # ic(stand, turn_nb)

    # ! creer le modif_form
    modif_form = Stand_modif_form()
    # ic(stand.start_trace.filter_by(turn_nb=turn_nb).count())
    if last_marker == -1 or not stand.start_trace.filter_by(turn_nb=turn_nb).count():
        modif_form.chrono.data = True
        modif_form.chrono.render_kw = {"disabled": ""}

    if modif_form.validate_on_submit():
        ic(
            modif_form.lat.data,
            modif_form.lng.data,
            modif_form.color.data,
            modif_form.name.data,
        )
        elev = get_points_elevation(
            [(assert400(modif_form.lat.data), assert400(modif_form.lng.data))]
        )
        elevation = elev[0]["elevation"] if elev else None
        new_stand = Stand(
            name=assert400(modif_form.name.data),
            lat=assert400(modif_form.lat.data),
            lng=assert400(modif_form.lng.data),
            elevation=elevation,
            parcours_id=parcours.id,
            color=Color(assert400(modif_form.color.data)),
            chrono=modif_form.chrono.data,
            start_stand=None,
            end_stand=None,
        )
        db.session.add(new_stand)
        db.session.commit()
        db.session.refresh(new_stand)

        nb_name = (
            Trace.query()
            .filter(Trace.name.contains(f"{stand.name} - {new_stand.name}"[:36]))
            .count()
        )
        old_trace = Trace.query().filter_by(start_id=stand.id, turn_nb=turn_nb).first()
        name = f"{stand.name} - {new_stand.name}{f' ({nb_name})' if nb_name else ''}"
        new_trace = Trace(
            name=name,
            parcours_id=parcours.id,
            start_id=stand.id,
            end_id=new_stand.id,
            turn_nb=turn_nb,
        )
        db.session.add(new_trace)

        # ic(stand.start_trace.filter_by(turn_nb=turn_nb+1).all(), stand.start_trace.filter_by(turn_nb=turn_nb+1).all())
        if stand.end_stand:  # c'est le dernier
            # ic('dernier')
            parcours.end_stand.end_stand = None
            new_stand.end_stand = parcours.id
        else:
            # ic('pas dernier')
            assert400(old_trace).start_id = new_stand.id
        db.session.commit()

        return redirect(
            url_for(
                "admin.parcours.modify_parcours",
                event_name=event.name,
                parcours_name=parcours.name,
                force_modif=request.args.get("force_modif", None),
            )
        )
    ic(modif_form.errors)
    return render_modify_parcours(
        event, parcours, "new", modif_form, last_marker=last_marker
    )


@set_route(
    parcours_bp,
    "/event/<event_name>/parcours/<parcours_name>/new/<int:last_marker>/<int:stand_id>",
    methods=["POST", "GET"],
)
@login_required
@admin_required
def new_step(
    event_name: str, parcours_name: str, last_marker: int, stand_id: int
) -> str | Response:
    event = Event.query().filter_by(name=event_name).first_or_404()
    parcours = assert404(event.parcours.filter_by(name=parcours_name).first())
    end_stand = assert404(parcours.stands.filter_by(id=stand_id).first())

    ic("step 1")
    # trouve le marker qui est le debut de la traces
    turn_nb = 1
    start_stand: Stand = parcours.start_stand
    for _ in range(last_marker):
        start_stand = assert400(
            start_stand.start_trace.filter_by(turn_nb=turn_nb).first()
        ).end
        if start_stand == parcours.start_stand:
            turn_nb += 1
    # ic(start_stand, turn_nb)
    ic("step 2")
    nb_name = (
        Trace.query()
        .filter(Trace.name.contains(f"{start_stand.name} - {end_stand.name}"[:36]))
        .count()
    )
    old_trace = (
        Trace.query().filter_by(start_id=start_stand.id, turn_nb=turn_nb).first()
    )

    name = f"{start_stand.name} - {end_stand.name}{f' ({nb_name})' if nb_name else ''}"
    new_trace = Trace(
        name=name,
        parcours_id=parcours.id,
        start_id=start_stand.id,
        end_id=end_stand.id,
        turn_nb=turn_nb,
    )

    if end_stand == parcours.start_stand:
        for nb in range(turn_nb + 1, parcours.get_nb_turns() + 1):
            for trace in parcours.traces.filter_by(turn_nb=nb).all():
                trace.turn_nb += 1
    else:
        # ic(parcours.traces.filter_by(turn_nb=turn_nb).all(), end_stand)
        if (
            parcours.traces.filter_by(turn_nb=turn_nb)
            .filter(or_(Trace.start_id == end_stand.id, Trace.end_id == end_stand.id))
            .count()
            != 0
        ):
            flash(
                "ce stand ne peut pas etre utilisé car il est deja utilise pour cette etape",
                "warning",
            )
            return redirect(
                url_for(
                    "admin.parcours.modify_parcours",
                    event_name=event.name,
                    parcours_name=parcours.name,
                    force_modif=request.args.get("force_modif", None),
                )
            )

    db.session.add(new_trace)
    if start_stand == parcours.end_stand:
        parcours.end_stand.end_stand = None
        end_stand.end_stand = parcours.id
    else:
        assert400(old_trace).start_id = end_stand.id

    db.session.commit()

    return render_modify_parcours(event, parcours)


@set_route(
    parcours_bp,
    "/event/<event_name>/parcours/<parcours_name>/trace/<int:trace_id>/delete",
)
@login_required
@admin_required
def delete_trace(event_name: str, parcours_name: str, trace_id: int) -> str | Response:
    event = Event.query().filter_by(name=event_name).first_or_404()
    parcours = assert404(event.parcours.filter_by(name=parcours_name).first())
    trace = parcours.traces.filter_by(id=trace_id).first()
    # ic(trace, trace.end, parcours.start_stand, trace.end == parcours.start_stand, bool(trace))

    if trace is None:
        # ic('trace == None')
        return redirect(
            url_for(
                "admin.parcours.modify_parcours",
                event_name=event.name,
                parcours_name=parcours.name,
                force_modif=request.args.get("force_modif", None),
            )
        )

    if trace.end == parcours.start_stand:
        # ic('fin de la trace -> debut du parcours')
        if trace.is_last_trace():
            # ic('derniere du parcours')
            parcours.end_stand.end_stand = None
            trace.start.end_stand = parcours.id
            db.session.delete(trace)
            db.session.commit()
        else:
            stands_last_turn = set[int]()
            for loop_trace in parcours.traces.filter_by(turn_nb=trace.turn_nb).all():
                stands_last_turn.add(loop_trace.end.id)
                stands_last_turn.add(loop_trace.start.id)
            stands_next_turn = set[int]()
            for loop_trace in parcours.traces.filter_by(
                turn_nb=trace.turn_nb + 1
            ).all():
                stands_next_turn.add(loop_trace.end.id)
                stands_next_turn.add(loop_trace.start.id)
            if any(
                [
                    stand_id in stands_last_turn and stand_id != parcours.start_stand.id
                    for stand_id in stands_next_turn
                ]
            ):
                flash(
                    "cette etape n'est pas supprimable car elle créerais une boucle hors du parcours",
                    "danger",
                )
                return redirect(
                    url_for(
                        "admin.parcours.modify_parcours",
                        event_name=event.name,
                        parcours_name=parcours.name,
                        force_modif=request.args.get("force_modif", None),
                    )
                )

            # ic('pas la derniere du parcours')
            # ic(trace.get_next_trace())
            next = assert400(trace.get_next_trace())
            next.start_id = trace.start_id
            # ic(next, trace.start_id)
            db.session.commit()
            db.session.delete(trace)
            db.session.commit()
            # ic(trace.turn_nb+1,parcours.get_nb_turns()+1)
            for nb in range(trace.turn_nb + 1, parcours.get_nb_turns() + 1):
                for trace in parcours.traces.filter_by(turn_nb=nb).all():
                    trace.turn_nb -= 1
            db.session.commit()
    elif trace.end == parcours.end_stand:
        # ic('fin de la trace -> fin du parcours')
        trace.end.end_stand = None
        trace.start.end_stand = parcours.id
        if trace.end.start_trace.filter_by(turn_nb=trace.turn_nb).count() == 0:
            db.session.delete(trace.end)
        db.session.delete(trace)
        db.session.commit()
    elif assert400(trace.get_next_trace()).end.id == parcours.start_stand.id:
        # ic('allée d\'un allée retour')
        next_trace = trace.get_next_trace()
        # ic(next_trace)
        if (
            trace.end.start_trace.filter_by(turn_nb=trace.turn_nb).count() == 1
        ):  # un seul : la trace à supprimer
            db.session.delete(trace.end)
        # ic(next_trace, trace)
        db.session.delete(next_trace)
        db.session.delete(trace)
        for nb in range(trace.turn_nb + 1, parcours.get_nb_turns() + 1):
            for trace in parcours.traces.filter_by(turn_nb=nb).all():
                trace.turn_nb -= 1

        db.session.commit()
    else:
        # ic('allée normale')
        assert400(trace.get_next_trace()).start_id = trace.start_id

        # ic(trace.end.start_trace.filter_by(turn_nb=trace.turn_nb+1).all(), trace.end.start_trace.filter_by(turn_nb=trace.turn_nb).all())
        if (
            trace.end.start_trace.filter_by(turn_nb=trace.turn_nb).count() == 0
        ):  # un seul : la trace à supprimer
            # ic('delete the stand')
            db.session.delete(trace.end)

        db.session.delete(trace)
        db.session.commit()

    return redirect(
        url_for(
            "admin.parcours.modify_parcours",
            event_name=event.name,
            parcours_name=parcours.name,
            force_modif=request.args.get("force_modif", None),
        )
    )


def render_modify_parcours(
    event: Event,
    parcours: ParcoursVersion,
    modif_form_type: Literal["marker", "trace", "new"] | None = None,
    modif_form: FlaskForm | None = None,
    **kwargs: Any,
) -> str | Response:  # pyright: ignore[reportExplicitAny, reportAny]
    user = current_user
    modif = (
        not bool(parcours.editions.count()) or request.args.get("force_modif") == "true"
    )
    ic(modif, request.args)
    if not (modif_form_type and modif_form):
        modif_form_type = None
        modif_form = None

    # ? formulaire pour le nom du parcours
    name_form = Parcours_name_form(
        data={"name": parcours.name, "description": parcours.description}
    )
    if modif_form:
        name_form.name.data = parcours.name
        name_form.description.data = parcours.description
    if name_form.validate_on_submit() and not modif_form:
        if (
            name_form.name.data == parcours.name
            or not event.parcours.filter_by(name=name_form.name.data).first()
        ):
            # le nom peut etre utilisé
            parcours.name = assert400(name_form.name.data)
            parcours.description = assert400(name_form.description.data)
            db.session.commit()
            flash("name saved", "success")
            return redirect(
                url_for(
                    "admin.parcours.modify_parcours",
                    event_name=event.name,
                    parcours_name=parcours.name,
                    force_modif=request.args.get("force_modif", None),
                )
            )
        else:
            name_form.name.errors = list(name_form.name.errors) + [
                "vous utiliser deja ce nom."
            ]

    map_data = create_map_and_alt_graph(
        parcours,
        modif=modif,
        current_stand_id=cast(int, kwargs["stand"].id) if "stand" in kwargs else None,
        current_trace_id=cast(str, kwargs["trace"].id) if "trace" in kwargs else None,
    )

    (
        element_name,
        last_path_name,
        next_path_name,
        markers_name,
        program_list,
        map,
        graph,
    ) = map_data

    from branca.element import Figure

    # ? render the map
    root = cast(Figure, map.get_root())
    root.width = "100%"
    root.height = "450px"
    root.render()  # pyright: ignore[reportUnknownMemberType]

    header = root.header.render()  # pyright: ignore[reportUnknownMemberType]
    body = root.html.render()  # pyright: ignore[reportUnknownMemberType]
    script = root.script.render()  # pyright: ignore[reportUnknownMemberType]

    folium_map = {"header": header, "body": body, "script": script}
    return render_template(
        "modify_parcours.html",
        user_data=user,
        event_data=event,
        parcours_data=parcours,
        name_form=name_form,
        folium_map=folium_map,
        map_name=map.get_name(),
        element_name=element_name,
        path_names={"last": last_path_name, "next": next_path_name}
        if last_path_name
        else markers_name,
        program_list=program_list,
        modif_form=modif_form,
        modif_form_type=modif_form_type,
        graph=graph,
        event_modif=True,
        modif=modif,
        **kwargs,
    )
