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

import sentry_sdk
import locale
from collections.abc import Callable
from datetime import date, datetime
from functools import wraps
from typing import (
    Any,
    Final,
    Generic,
    ParamSpec,
    Self,
    TypeVar,
    cast,
    override,
)

from flask import (
    Blueprint,
    Flask,
    abort,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask.json.provider import DefaultJSONProvider
from flask.typing import ResponseReturnValue
from flask_babel import Babel, _, gettext
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user, login_required
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_sse import sse
from icecream import install
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, Query
from werkzeug import exceptions
from werkzeug.wrappers.response import Response

from .config import FlaskConfig, cdv_config

if cdv_config.SENTRY_ENABLED:
    sentry_sdk.init(
        dsn=cdv_config.SENTRY_DNS,
        traces_sample_rate=0.01,  # 1% of transactions — adjust to your needs
        auto_session_tracking=False,  # GlitchTip does not support sessions
        # enable_logs=True,  # Opt-in: send logs to GlitchTip (uses disk space)
        release="0.1.0",
        environment=cdv_config.SENTRY_ENVIRONMENT,
    )


install()

# met la langue en francais pour le formatage des dates
locale.setlocale(locale.LC_TIME, "")

app = Flask(
    __name__,
)
app.config.from_object(FlaskConfig)
app.jinja_env.add_extension("jinja2.ext.loopcontrols")

# sse blueprint
app.register_blueprint(sse, url_prefix="/stream")


DEFAULT_PROFIL_PIC: Final[str] = "icone.png"
LANGAGES: Final[tuple[str, ...]] = ("de", "fr", "en")
if app.debug:
    LANGAGES += ("ids", "pseudo")  # pyright: ignore[reportConstantRedefinition, reportGeneralTypeIssues]
PICTURE_SIZE: Final[tuple[int, int]] = (200, 200)


class CustomJSONProvider(DefaultJSONProvider):
    @override
    def default(self, obj: Any) -> Any:  # pyright: ignore[reportAny, reportIncompatibleMethodOverride]
        if isinstance(obj, datetime) or isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)  # pyright: ignore[reportAny]


app.json = CustomJSONProvider(app)


T = TypeVar("T")


class BaseQuery(Query[T], Generic[T]):
    def first_or_404(self, description: str | None = None) -> T:
        result = self.first()
        if result is None:
            abort(404, description)
        return result

    def get_or_404(
        self, ident: Any | tuple[Any, ...], description: str | None = None
    ) -> T:
        result = self.get(ident)
        if result is None:
            abort(404, description)
        return result

    @override
    def get(self, ident: Any | tuple[Any, ...]) -> T | None:
        return super().get(ident)


class Base(DeclarativeBase, MappedAsDataclass):  # pyright: ignore[reportUnsafeMultipleInheritance]
    @classmethod
    def query(cls):
        return cast(BaseQuery[Self], db.session.query(cls))


db = SQLAlchemy(app, model_class=Base, session_options={"query_cls": BaseQuery})

migrate = Migrate(app, db)

socketio = SocketIO(app)

bcrypt = Bcrypt(app)


login_manager = LoginManager(app)
login_manager.login_view = "users.login"
login_manager.login_message_category = "info"

# ? instansiate flask babel
# if app.debug:
#     old = ".venv/Lib/site-packages/babel/locale-data/fr_CH.dat"
#     new = (
#         ".venv/Lib/site-packages/babel/locale-data/pseudo.dat",
#         ".venv/Lib/site-packages/babel/locale-data/ids.dat",
#     )
#     for file in new:
#         if not os.path.exists(file):
#             with open(old, "rb") as file1:
#                 with open(file, "+wb") as file2:
#                     file2.write(file1.read())

#     from babel.core import LOCALE_ALIASES

#     LOCALE_ALIASES["pseudo"] = "pseudo"
#     LOCALE_ALIASES["ids"] = "ids"


def get_locale() -> str:
    # if a user is logged in, use the locale from the user settings
    # ic(session.get('lang'), request.accept_languages.best_match(LANGAGES))
    if session.get("lang"):  # pyright: ignore[reportUnknownMemberType]
        return cast(str, session["lang"])
    # otherwise try to guess the language from the user accept
    # header the browser transmits.  We support de/fr/en in this
    # example.  The best match wins.
    return request.accept_languages.best_match(LANGAGES, default="en")


babel = Babel(app, locale_selector=get_locale)

from chrono_des_vignes.models import User  # noqa: E402


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.query(User).filter_by(id=user_id).first()


param = ParamSpec("param")
ret = TypeVar("ret")


def admin_required(func: Callable[param, ret]) -> Callable[param, ret | Response]:
    """
    Modified login_required decorator to restrict access to admin group.
    """

    @login_required
    @wraps(func)
    def decorated_view(*args: param.args, **kwargs: param.kwargs) -> ret | Response:
        if not current_user.admin:
            flash(_("flash.error.mustadmin"), "danger")
            return redirect(url_for("home"))
        if (
            kwargs.get("event_name")
            and not current_user.creations.filter_by(
                name=kwargs.get("event_name")
            ).first()
        ):
            flash(_("flash.error.wrongadminevent"), "danger")
            return redirect(url_for("home"))
        return func(*args, **kwargs)

    return decorated_view


def lang_url_for(
    endpoint: str,
    *,
    _anchor: str | None = None,
    _method: str | None = None,
    _scheme: str | None = None,
    _external: bool | None = None,
    **values: Any,  # pyright: ignore[reportAny]
) -> str:
    if "static" in endpoint or values.get("lang"):
        return url_for(
            endpoint,
            _anchor=_anchor,
            _method=_method,
            _scheme=_scheme,
            _external=_external,
            **values,
        )
    lang: str | None = _("app.lang")
    if endpoint.startswith("doc"):
        if lang == "fr":
            lang = None
        url = url_for(
            endpoint,
            _anchor=_anchor,
            _method=_method,
            _scheme=_scheme,
            _external=_external,
            lang=lang,
            **values,
        )
        if url[-1] != "/":
            url += "/"
        return url
    if lang == request.accept_languages.best_match(LANGAGES):
        return url_for(
            endpoint,
            _anchor=_anchor,
            _method=_method,
            _scheme=_scheme,
            _external=_external,
            **values,
        )
    return url_for(
        endpoint,
        _anchor=_anchor,
        _method=_method,
        _scheme=_scheme,
        _external=_external,
        lang=lang,
        **values,
    )


@app.context_processor
def jinja_context():
    return dict(
        _=gettext,
        url_for=lang_url_for,
        now=datetime.now(),
        date=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
    )


routeP = ParamSpec("routeP")
routeR = TypeVar("routeR", bound=ResponseReturnValue)


def set_route(
    blueprint: Flask | Blueprint,
    path: str,
    **options: Any,  # pyright: ignore[reportAny]
) -> Callable[..., Callable[routeP, routeR]]:
    def decorator(func: Callable[routeP, routeR]) -> Callable[routeP, routeR]:
        @blueprint.route(f"/<lang>{path}", **options)
        @blueprint.route(path, **options)
        @wraps(func)
        def wrap(*args: routeP.args, **kwargs: routeP.kwargs):
            lang = kwargs.pop("lang", None)
            # ic('hey', lang, path, func.__name__)
            if lang is None:
                lang = request.accept_languages.best_match(LANGAGES)
            if lang not in LANGAGES:
                return abort(404)
            session["lang"] = lang
            return func(*args, **kwargs)

        return wrap

    return decorator


# ? error Handling


@app.errorhandler(exceptions.Forbidden)
@app.errorhandler(exceptions.InternalServerError)
@app.errorhandler(exceptions.MethodNotAllowed)
@app.errorhandler(exceptions.NotFound)
@app.errorhandler(exceptions.TooManyRequests)
@app.errorhandler(exceptions.BadRequest)
@app.errorhandler(exceptions.ImATeapot)
def http_error(error: exceptions.HTTPException) -> Response:
    html = render_template("error/simple_error.html", error=error)
    return make_response(html, error.code)


# ? end error Handling

# defini les pages du site web
from chrono_des_vignes.users import users  # noqa: E402

app.register_blueprint(users)

from chrono_des_vignes.admin import admin  # noqa: E402

app.register_blueprint(admin)

from chrono_des_vignes.view import view  # noqa: E402

app.register_blueprint(view)

if app.debug:
    from chrono_des_vignes.dev import dev

    app.register_blueprint(dev)

from chrono_des_vignes.livetrack import livetrack  # noqa: E402

app.register_blueprint(livetrack)

from .api import api_blueprint  # noqa: E402

app.register_blueprint(api_blueprint)

from chrono_des_vignes import routes as routes  # noqa: E402
