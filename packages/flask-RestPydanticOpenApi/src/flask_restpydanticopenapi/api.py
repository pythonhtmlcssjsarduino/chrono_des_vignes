from __future__ import annotations

from collections.abc import Callable

from flask import Flask, Response

from flask_restpydanticopenapi.openapi import OpenApiBuilder
from flask_restpydanticopenapi.resource import Resource
from flask_restpydanticopenapi.utils import generate_url


class Api:
    def __init__(self, app: Flask | None = None, api_prefix: str = "/api") -> None:
        if app is not None:
            self.init_app(app, api_prefix)

    def init_app(self, app: Flask, api_prefix: str = "/api") -> None:
        self._builder: OpenApiBuilder = OpenApiBuilder(app.url_map.converters)  # pyright: ignore[reportUninitializedInstanceVariable]
        self.api_prefix: str = api_prefix  # pyright: ignore[reportUninitializedInstanceVariable]
        self._app: Flask = app  # pyright: ignore[reportUninitializedInstanceVariable]

        @app.route(f"{api_prefix}/swagger.json")
        def swagger():  # pyright: ignore[reportUnusedFunction]
            return Response(self.get_openapi_spec(), mimetype="application/json")

    def register[T: type[Resource]](self, rule: str, version: int) -> Callable[[T], T]:
        def decorator(cls: T):

            self._add_resource(cls, rule, version)
            return cls

        return decorator

    def _add_resource(self, cls: type[Resource], rule: str, version: int) -> None:
        self._app.add_url_rule(
            generate_url(rule, version, self.api_prefix),
            view_func=cls.as_view(f"v{version}_{cls.__name__.lower()}"),
        )
        self._builder.add_resource(cls, rule, version, self.api_prefix)

    def version(self, version: int) -> ApiVersion:
        return ApiVersion(version, self)

    def get_openapi_spec(self):
        return self._builder.get_openapi_spec()


class ApiVersion:
    def __init__(self, version: int, api: Api) -> None:
        self.version: int = version
        self.api: Api = api

    def register[T: type[Resource]](
        self,
        rule: str,
    ):
        return self.api.register(rule, self.version)
