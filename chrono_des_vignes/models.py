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
# or from my github https://github.com/pythonhtmlcssjsarduino/chrono_des_vignes
"""

from __future__ import annotations
from html import escape
from warnings import deprecated
from flask import abort
from sqlalchemy.orm import AppenderQuery, DynamicMapped, Mapper, mapped_column, Mapped
from chrono_des_vignes import db, DEFAULT_PROFIL_PIC, Base
from sqlalchemy_utils import ColorType as ColorType_sql_utils  # pyright: ignore[reportMissingTypeStubs]
from colour import Color
from flask_login import UserMixin
from datetime import datetime, timedelta
from chrono_des_vignes.lib import assert400, calc_points_dist
from typing import Any, NamedTuple, TypedDict, cast
from collections.abc import Iterable, Iterator
from markdown import markdown
from sqlalchemy import (
    asc,
    desc,
    not_,
    Table,
    Integer,
    ForeignKey,
    DateTime,
    String,
    Boolean,
    Text,
    Float,
    Column,
)
from sqlalchemy.orm import relationship
from sqlalchemy.inspection import inspect
from ast import literal_eval

Model = Base


class BaseAppenderQuery[T](AppenderQuery[T]):
    def first_or_404(self, description: str | None = None) -> T:
        result = self.first()
        if result is None:
            abort(404, description)
        return result


md_extentions: list[str] = ["admonition", "markdown.extensions.tables"]


def get_html_from_markdown(markdown_text: str) -> str:
    return markdown(
        escape(markdown_text),
        extensions=md_extentions,
        extension_configs={},
        output_format="html",
    )


def get_column_max_length[T](table: type[T], column_name: str):
    mapper = cast(Mapper[T], inspect(table, True))
    column = mapper.columns[column_name]

    if isinstance(column.type, String) and column.type.length is not None:
        return column.type.length
    # max int possible
    return 2147483647


class ColorType(ColorType_sql_utils):
    STORE_FORMAT: str = "hex_l"


class Point(NamedTuple):
    lat: float
    lng: float
    alt: float | None = None


editions_parcours: Table = db.Table(
    "editions_parcours",
    Column("edition_id", Integer, ForeignKey("edition.id")),
    Column("parcours_id", Integer, ForeignKey("parcours_version.id")),
)

passagekey_stand: Table = db.Table(
    "passagekey_stand",
    Column("passage_key_id", Integer, ForeignKey("passage_key.id")),
    Column("stand_id", Integer, ForeignKey("stand.id")),
)


class User(UserMixin, Model):
    id: Mapped[int] = mapped_column(primary_key=True, repr=True, init=False)

    name: Mapped[str] = mapped_column(String(40), nullable=False, repr=False)
    lastname: Mapped[str] = mapped_column(String(40), nullable=False, repr=False)
    password: Mapped[str] = mapped_column(String(80), nullable=False, repr=False)
    password_changed: Mapped[datetime] = mapped_column(
        nullable=True, repr=False, init=False
    )
    username: Mapped[str] = mapped_column(
        String(40), nullable=False, unique=True, repr=True
    )
    email: Mapped[str | None] = mapped_column(String(80), nullable=True, repr=False)
    phone: Mapped[str | None] = mapped_column(String(25), nullable=True, repr=False)
    datenaiss: Mapped[datetime] = mapped_column(nullable=False, repr=False)

    admin: Mapped[bool] = mapped_column(nullable=False, default=False, repr=True)
    creation_date: Mapped[datetime] = mapped_column(
        nullable=False, default_factory=datetime.now, repr=False
    )
    avatar: Mapped[str] = mapped_column(
        String(80), nullable=False, default=DEFAULT_PROFIL_PIC, repr=False
    )

    creations: DynamicMapped[Event] = relationship(
        "Event",
        back_populates="createur",
        lazy="dynamic",
        query_class=BaseAppenderQuery,
        init=False,
        repr=False,
    )
    inscriptions: DynamicMapped[Inscription] = relationship(
        "Inscription",
        back_populates="inscrit",
        lazy="dynamic",
        query_class=BaseAppenderQuery,
        init=False,
        repr=False,
    )
    __tablename__: str = "user"


class Event(Model):
    id: Mapped[int] = mapped_column(primary_key=True, repr=True, init=False)
    name: Mapped[str] = mapped_column(
        String(40), nullable=False, unique=True, repr=True
    )

    createur_id: Mapped[int] = mapped_column(
        ForeignKey("user.id"), nullable=False, repr=False
    )
    createur: Mapped[User] = relationship(
        "User", back_populates="creations", lazy="select", repr=True, init=False
    )

    creation_date: Mapped[datetime] = mapped_column(
        nullable=False, default_factory=datetime.now, repr=False
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False, default="", repr=False
    )

    parcours: DynamicMapped[Parcours] = relationship(
        "Parcours",
        back_populates="event",
        lazy="dynamic",
        repr=False,
        init=False,
    )
    editions: DynamicMapped[Edition] = relationship(
        "Edition", back_populates="event", lazy="dynamic", repr=False, init=False
    )
    inscrits: DynamicMapped[Inscription] = relationship(
        "Inscription", back_populates="event", lazy="dynamic", repr=False, init=False
    )
    passage_keys: DynamicMapped[PassageKey] = relationship(
        "PassageKey", back_populates="event", lazy="dynamic", repr=False, init=False
    )
    __tablename__: str = "event"

    @property
    def description_html(self) -> str:
        return get_html_from_markdown(self.description)

    @deprecated("use the property instead")
    def get_unique_inscrits(self):
        return self.unique_inscrits

    @property
    def unique_inscrits(self):
        uniques: list[Inscription] = []
        ids: set[int] = set()
        for inscrit in self.inscrits.all():
            if inscrit.inscrit.id not in ids:
                ids.add(inscrit.inscrit.id)
                uniques.append(inscrit)
        return uniques


class Parcours(Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    versions: DynamicMapped[ParcoursVersion] = relationship(
        "ParcoursVersion",
        back_populates="parcours",
        foreign_keys="ParcoursVersion.parcours_id",
        lazy="dynamic",
        init=False,
    )
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("event.id"), nullable=False
    )
    event: Mapped[Event] = relationship(
        "Event", back_populates="parcours", lazy="select", init=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    __tablename__: str = "parcours"

    @property
    def last_version(self):
        return assert400(
            self.versions.order_by(desc(ParcoursVersion.creation_date)).first()
        )


class ParcoursVersion(Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    parcours_id: Mapped[int] = mapped_column(Integer, ForeignKey("parcours.id"))
    parcours: Mapped[Parcours] = relationship(
        "Parcours", back_populates="versions", lazy="select", init=False
    )
    stands: DynamicMapped[Stand] = relationship(
        "Stand",
        back_populates="parcours_version",
        foreign_keys="Stand.parcours_id",
        lazy="dynamic",
        init=False,
    )
    traces: DynamicMapped[Trace] = relationship(
        "Trace",
        back_populates="parcours_version",
        foreign_keys="Trace.parcours_id",
        lazy="dynamic",
        init=False,
    )
    editions: DynamicMapped[Edition] = relationship(
        "Edition",
        secondary=editions_parcours,
        back_populates="parcours_version",
        lazy="dynamic",
        init=False,
    )
    inscriptions: DynamicMapped[Inscription] = relationship(
        "Inscription", back_populates="parcours_version", lazy="dynamic", init=False
    )

    creation_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default_factory=datetime.now
    )
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    __tablename__: str = "parcours_version"

    # region
    @property
    def name(self):
        return self.parcours.name

    @property
    def event_id(self):
        return self.parcours.event_id

    @property
    def event(self):
        return self.parcours.event

    @property
    def start(self):
        if Stand.query().filter(Stand.parcours_id == self.id).count() == 1:
            return assert400(Stand.query().filter(Stand.parcours_id == self.id).first())
        return assert400(
            Trace.query()
            .filter(Trace.parcours_id == self.id)
            .order_by(asc(Trace.index))
            .first()
        ).start

    @property
    def end(self):
        if Stand.query().filter(Stand.parcours_id == self.id).count() == 1:
            return assert400(Stand.query().filter(Stand.parcours_id == self.id).first())
        return assert400(
            Trace.query()
            .filter(Trace.parcours_id == self.id)
            .order_by(desc(Trace.index))
            .first()
        ).end

    @property
    def description_html(self) -> str:
        return get_html_from_markdown(self.description)

    def __iter__(self) -> Iterator[Stand | Trace]:
        yield self.start
        traces = (
            Trace.query()
            .filter(Trace.parcours_id == self.id)
            .order_by(asc(Trace.index))
            .all()
        )
        if len(traces) == 0:
            return

        for trace in traces:
            yield trace
            yield trace.end

    def iter_chrono_list(self):
        return iter(
            Stand.query().filter(Stand.parcours_id == self.id, Stand.chrono).all()
        )

    def get_chrono_dists(self):
        dist: float = 0
        dist_list: list[float] = []
        for e in self:
            if isinstance(e, Stand):
                if e.chrono:
                    dist_list.append(dist)
            else:
                dist += e.get_dist()
        return dist_list

    # endregion


class Stand(Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    parcours_id: Mapped[int] = mapped_column(Integer, ForeignKey("parcours_version.id"))
    elevation: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    parcours_version: Mapped[ParcoursVersion] = relationship(
        "ParcoursVersion",
        back_populates="stands",
        foreign_keys=[parcours_id],
        lazy="select",
        init=False,
    )
    color: Mapped[Color] = mapped_column(
        ColorType, nullable=False, default_factory=lambda: Color("red")
    )
    chrono: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # traces qui partent de ce stand
    start_trace: DynamicMapped[Trace] = relationship(
        "Trace",
        back_populates="start",
        foreign_keys="Trace.start_id",
        lazy="dynamic",
        init=False,
    )
    # traces qui finissent a ce stand
    end_trace: DynamicMapped[Trace] = relationship(
        "Trace",
        back_populates="end",
        foreign_keys="Trace.end_id",
        lazy="dynamic",
        init=False,
    )
    passage_keys: DynamicMapped[PassageKey] = relationship(
        "PassageKey",
        secondary=passagekey_stand,
        back_populates="stands",
        lazy="dynamic",
        init=False,
    )
    __tablename__: str = "stand"


class Trace(Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    index: Mapped[int] = mapped_column(Integer, init=True)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    parcours_id: Mapped[int] = mapped_column(Integer, ForeignKey("parcours_version.id"))
    parcours_version: Mapped[ParcoursVersion] = relationship(
        "ParcoursVersion", back_populates="traces", lazy="select", init=False
    )
    start_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stand.id"), nullable=False
    )
    start: Mapped[Stand] = relationship(
        "Stand",
        back_populates="start_trace",
        foreign_keys=[start_id],
        lazy="select",
        init=False,
    )
    end_id: Mapped[int] = mapped_column(Integer, ForeignKey("stand.id"), nullable=False)
    end: Mapped[Stand] = relationship(
        "Stand",
        back_populates="end_trace",
        foreign_keys=[end_id],
        lazy="select",
        init=False,
    )
    _trace: Mapped[str] = mapped_column(
        Text, name="trace", nullable=False, default="[]"
    )
    __tablename__: str = "trace"

    # region fonctions
    def __iter__(self) -> Iterator[Point]:
        return iter(self.path)

    def __len__(self) -> int:
        return len(self.path)

    @property
    def path(self):
        return [
            Point(*point)
            for point in cast(
                list[tuple[float, float, float]], literal_eval(self._trace)
            )
        ]

    @staticmethod
    def check_path(path: Any):  # pyright: ignore[reportAny]
        if not isinstance(path, Iterable):
            return None
        checked: list[Point] = []
        for p in path:
            if not isinstance(p, Iterable):
                return None
            p = list(p)
            p[2] = p[2] if len(p) > 2 else None
            if (
                len(p) not in (2, 3)
                or not isinstance(p[0], (float, int))
                or not isinstance(p[1], (float, int))
                or not (isinstance(p[2], (float, int)) or p[2] is None)
            ):
                return None
            checked.append(Point(p[0], p[1], p[2]))
        return checked

    @path.setter
    def path(self, path: list[Point]):
        self._trace = str([tuple(p) for p in path])

    """
    Deprecated do not use it use the path property instead
    """

    @property
    def trace(self):
        return self._trace

    """
    Deprecated do not use it use the path property instead
    """

    @trace.setter
    def trace(self, trace: str):
        self._trace = trace

    @deprecated("use the Trace.path proprety instead")
    def set_trace(
        self, trace: Iterable[Point | tuple[float, float, float | None]]
    ) -> None:
        """
        sterilise et defini la valeure du champ trace
        !!! ne commit pas les changement !!
        """
        sterilised_trace: list[tuple[float, float, float | None]] = []
        for point in trace:
            sterilised_trace.append((point[0], point[1], point[2]))
        self._trace = str(sterilised_trace)

    def has_alt(self) -> bool:
        return all((bool(point.alt) for point in self))

    def get_dist(self) -> float:
        dist: float = 0
        last_point = self.start.lat, self.start.lng
        for lat, lng, _alt in self:
            dist += calc_points_dist(lat, lng, last_point[0], last_point[1])
            last_point = lat, lng
        dist += calc_points_dist(
            self.end.lat, self.end.lng, last_point[0], last_point[1]
        )
        return dist

    def is_last_trace(self):
        # ic(self.end == self.parcours.end_stand and self.end.end_trace.filter_by(turn_nb=self.turn_nb+1).count()==0, self.end , self.parcours.end_stand, self.end.end_trace.filter_by(turn_nb=self.turn_nb+1).count())
        return self.end == self.parcours_version.end

    def is_first_trace(self):
        return self.start == self.parcours_version.start

    def get_next_trace(self):
        return (
            Trace.query()
            .filter(
                Trace.parcours_id == self.parcours_id, Trace.index == self.index + 1
            )
            .first()
        )

    def get_last_trace(self):
        return (
            Trace.query()
            .filter(
                Trace.parcours_id == self.parcours_id, Trace.index == self.index - 1
            )
            .first()
        )

    # endregion


class Edition(Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("event.id"), nullable=False
    )
    event: Mapped[Event] = relationship(
        "Event", back_populates="editions", lazy="select", init=False
    )
    parcours_version: DynamicMapped[ParcoursVersion] = relationship(
        "ParcoursVersion",
        secondary=editions_parcours,
        back_populates="editions",
        lazy="dynamic",
        init=False,
    )
    inscriptions: DynamicMapped[Inscription] = relationship(
        "Inscription", back_populates="edition", lazy="dynamic", init=False
    )
    edition_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    first_inscription: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_inscription: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    creation_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default_factory=datetime.now
    )
    rdv_lat: Mapped[float] = mapped_column(Float, nullable=False, default=46.58)
    rdv_lng: Mapped[float] = mapped_column(Float, nullable=False, default=6.52)
    passage_keys: DynamicMapped[PassageKey] = relationship(
        "PassageKey",
        back_populates="edition",
        foreign_keys="PassageKey.edition_id",
        lazy="dynamic",
        init=False,
    )
    __tablename__: str = "edition"

    @property
    def description_html(self) -> str:
        return get_html_from_markdown(self.description)


class Inscription(Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    inscrit: Mapped[User] = relationship(
        "User", back_populates="inscriptions", init=False
    )
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("event.id"), nullable=False
    )
    event: Mapped[Event] = relationship("Event", back_populates="inscrits", init=False)
    edition_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("edition.id"), nullable=False
    )
    edition: Mapped[Edition] = relationship(
        "Edition", back_populates="inscriptions", init=False
    )
    parcours_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("parcours_version.id"), nullable=False
    )
    parcours_version: Mapped[ParcoursVersion] = relationship(
        "ParcoursVersion", back_populates="inscriptions", init=False
    )
    dossard: Mapped[int | None] = mapped_column(Integer, nullable=True, init=False)
    passages: DynamicMapped[Passage] = relationship(
        "Passage", back_populates="inscription", lazy="dynamic", init=False
    )
    end: Mapped[str | None] = mapped_column(
        String(10), nullable=True, init=False
    )  # abandon, disqual, absent, finish or None

    data_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("inscription_data.id"), nullable=True
    )
    data: Mapped[InscriptionData | None] = relationship(
        "InscriptionData", back_populates="inscriptions", lazy="select", init=False
    )

    creation_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default_factory=datetime.now, init=False
    )
    present: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, init=False
    )
    __tablename__: str = "inscription"

    # region funcs
    def has_started(self) -> bool:
        return bool(self.passages.count())

    def get_last_passage(self):
        return self.passages.order_by(Passage.time_stamp.desc()).first()

    def get_first_passage(self):
        return self.passages.order_by(Passage.time_stamp.asc()).first()

    @property
    def status(self) -> str:
        if not self.has_started():
            return "pas partit"
        else:
            match self.end:
                case "abandon":
                    return "abandon"
                case "disqual":
                    return "disqualifié"
                case "absent":
                    return "absent"
                case "finish":
                    return "arrivé"
                case _:
                    return "en cours"

    @property
    def start_time(self):
        first_passage = self.get_first_passage()
        return first_passage.time_stamp if first_passage else None

    @property
    def last_time(self):
        last_passage = self.get_last_passage()
        return last_passage.time_stamp if last_passage else None

    def get_time(self) -> timedelta | None:
        if not self.has_started() or not self.last_time or not self.start_time:
            return None
        return self.last_time - self.start_time

    def get_run(self) -> list[bool | None]:
        user_passages: list[Passage] = self.passages.filter(
            Passage.time_stamp <= self.get_last_passage().time_stamp  # pyright: ignore[reportOptionalMemberAccess]
        ).all()
        run: list[bool | None] = []
        if len(user_passages) > 0:
            for stand in self.parcours_version.iter_chrono_list():
                if len(user_passages) > 0 and stand == user_passages[0].get_stand():
                    user_passages.pop(0)
                    run.append(True)
                elif len(user_passages) > 0:
                    run.append(False)
                else:
                    run.append(None)
        return run

    def has_all_right(self) -> bool:
        if not self.has_started():
            return False
        run = self.get_run()
        return all(run)

    def has_finish(self) -> bool:
        if not self.has_started():
            return False
        run = self.get_run()
        return run[-1] is not None

    @property
    def rank(self) -> int | str | None:
        if self.end != "finish":
            return {
                "abandon": "abandon",
                "disqual": "disqualifié",
                "absent": "absent",
            }.get(str(self.end), None)
        # all inscriptions that are in the same parcours and edition
        inscriptions = Inscription.query().filter(
            Inscription.parcours_version == self.parcours_version,
            Inscription.edition == self.edition,
        )
        # get all the inscription that there last time is smaller than this one
        inscriptions = inscriptions.filter(
            not_(Inscription.passages.any(Passage.time_stamp > self.get_time()))
        )  # type:ignore[no-untyped-call]
        # get only those that have finished
        inscriptions = inscriptions.filter(Inscription.end == "finish")
        return inscriptions.count() + 1

    # endregion


class PassageKey(Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("event.id"), nullable=False
    )
    event: Mapped[Event] = relationship(
        "Event", back_populates="passage_keys", init=False
    )
    edition_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("edition.id"), nullable=False
    )
    edition: Mapped[Edition] = relationship(
        "Edition", back_populates="passage_keys", init=False
    )
    stands: DynamicMapped[Stand] = relationship(
        "Stand",
        secondary=passagekey_stand,
        back_populates="passage_keys",
        lazy="dynamic",
        init=False,
    )
    passages: DynamicMapped[Passage] = relationship(
        "Passage", back_populates="key", lazy="dynamic", init=False
    )
    key: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    creation_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default_factory=datetime.now
    )
    __tablename__: str = "passage_key"


class SSE_data_key(TypedDict):
    id: int
    name: str
    key: str


class SSE_data_stand(TypedDict):
    id: int
    name: str


class SSE_data(TypedDict):
    id: int
    time_stamp: datetime
    inscription: dict[str, Any]
    key: SSE_data_key | None
    stand: SSE_data_stand | None


class Passage(Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    time_stamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    key_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("passage_key.id"), nullable=True
    )  # pas de key implique demmaré par l'admin
    key: Mapped[PassageKey | None] = relationship(
        "PassageKey", back_populates="passages", lazy="select", init=False
    )
    inscription_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("inscription.id"), nullable=False
    )
    inscription: Mapped[Inscription] = relationship(
        "Inscription", back_populates="passages", lazy="select", init=False
    )
    __tablename__: str = "passage"

    def get_stand(self) -> Stand:
        if self.key is None:
            stand = self.inscription.parcours_version.start
        else:
            stand = self.key.stands.filter_by(
                parcours_version=self.inscription.parcours_version
            ).first()
            if stand is None:
                stand = self.inscription.parcours_version.start
        return stand

    def SSE_data(self) -> SSE_data:
        return {
            "id": self.id,
            "time_stamp": self.time_stamp,
            "inscription": {
                "id": self.inscription.id,
                "dossard": self.inscription.dossard,
                "inscrit": {
                    "id": self.inscription.inscrit.id,
                    "username": self.inscription.inscrit.username,
                },
            },
            "key": {
                "id": key.id,
                "name": key.name,
                "key": key.key,
            }
            if (key := self.key) is not None
            else None,
            "stand": {"id": stand.id, "name": stand.name}
            if (stand := self.get_stand())
            else None,
        }


class InscriptionData(Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    inscriptions: DynamicMapped[Inscription] = relationship(
        "Inscription", back_populates="data", lazy="dynamic", init=False
    )

    comment: Mapped[str | None] = mapped_column(Text, nullable=True, default="")

    __tablename__: str = "inscription_data"
