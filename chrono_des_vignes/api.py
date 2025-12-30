'''
# Chrono Des Vignes
# a timing system for sports events
# 
# Copyright © 2025 Romain Maurer
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
'''
from __future__ import annotations
from functools import wraps
from typing import Any, Callable, Literal, Self
from flask import Blueprint, jsonify
from flask.typing import ResponseReturnValue
from flask_login import current_user
from icecream import ic

api_blueprint = Blueprint("api", __name__, url_prefix="/api")


class ApiBlueprint:
    @staticmethod
    def admin(
        package: str,
        error_callback: Callable[
            [ApiBlueprint, Literal["login", "admin", "event"]], ResponseReturnValue
        ]
        | None = None,
        version: str = "v1",):
        return ApiBlueprint(package, ["admin_required"], error_callback, version)
    @staticmethod
    def login(
        package: str,
        error_callback: Callable[
            [ApiBlueprint, Literal["login", "admin", "event"]], ResponseReturnValue
        ]
        | None = None,
        version: str = "v1",):
        return ApiBlueprint(package, ["login_required"], error_callback, version)
    def __init__(
        self,
        package: str,
        decorators: list[
            Callable[[Any], Any] | Literal["login_required", "admin_required"]
        ]
        | None = None,
        error_callback: Callable[
            [Self, Literal["login", "admin", "event"]], ResponseReturnValue
        ]
        | None = None,
        version: str = "v1",
    ):
        self.package: str = package.strip("/ ").replace(" ", "")
        self.version: str = version
        self.decorators: list[Callable[[Any], Any]] = [
            self.admin_required
            if dec == "admin_required"
            else (self.login_required if dec == "login_required" else dec)
            for dec in (decorators if decorators else [])
        ]
        self.unauthorized: Callable[
            [Self, Literal["login", "admin", "event"]], ResponseReturnValue
        ] = (
            error_callback
            if error_callback
            else lambda self, err: jsonify({"err": err})
        )

    def route[ret: ResponseReturnValue, **param](
        self, endpoint: str, method: Literal["GET", "POST", "PUT", "DELETE"] = "GET"
    ):
        """decorator for easely register api endpoint"""

        def decorateur(func: Callable[param, ret]) -> Callable[param, ret]:
            @wraps(func)
            def wrapper(*args: param.args, **kwargs: param.kwargs):
                return func(*args, **kwargs)

            for decorator in reversed(self.decorators):
                wrapper = decorator(wrapper)

            wrapper = api_blueprint.route(
                f"/{self.version}/{self.package}/{endpoint.lstrip('/')}",
                methods=[method],
            )(wrapper)
            return wrapper

        return decorateur

    def login_required[ret: ResponseReturnValue, **param](
        self, func: Callable[param, ret]
    ) -> Callable[param, ret | ResponseReturnValue]:
        def wrapper(*args: param.args, **kwargs: param.kwargs):
            if not current_user.is_authenticated:
                return self.unauthorized(self, "login")

            return func(*args, **kwargs)

        return wrapper

    def admin_required[ret: ResponseReturnValue, **param](
        self, func: Callable[param, ret]
    ) -> Callable[param, ret | ResponseReturnValue]:
        @self.login_required
        def wrapper(*args: param.args, **kwargs: param.kwargs):
            if not current_user.admin:
                return self.unauthorized(self, "admin")
            if (
                kwargs.get("event_id")
                and not current_user.creations.filter_by(
                    id=kwargs.get("event_id")
                ).first()
            ):
                return self.unauthorized(self, "event")
            return func(*args, **kwargs)

        return wrapper
