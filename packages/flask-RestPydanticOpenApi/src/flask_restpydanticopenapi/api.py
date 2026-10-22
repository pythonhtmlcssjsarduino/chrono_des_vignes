from __future__ import annotations

from collections.abc import Callable
from typing import NoReturn

from flask import Flask, Response, abort

from flask_restpydanticopenapi.authorize import ResultAcces, Scope
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

        app.extensions["flask_restpydanticopenapi"] = self

        @app.route(f"{api_prefix}/swagger.json")
        def swagger():
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

    def result_acces_denied_callback(
        self,
        result: object,
        access_dict: dict[Scope, ResultAcces],
    ) -> NoReturn:
        """callback called when an internal_getter is use to get an object regected by scopes"""
        abort(
            403,
            description=f"Access denied to the resource : {type(result).__name__}, scopes: {';'.join(f'{k.name}:{v.name}' for k, v in access_dict.items())}",
        )

    def result_as_read_only_callback[T: object](self, result: T) -> T:  # pyright: ignore[reportUnusedParameter]
        """callback called when an internal_getter is use to get an object regected by scopes but the result is read only"""
        raise NotImplementedError(
            "the result_as_read_only_callback must be implemented to use the read only mode of internal_getter"
        )


class ApiVersion:
    def __init__(self, version: int, api: Api) -> None:
        self.version: int = version
        self.api: Api = api

    def register[T: type[Resource]](
        self,
        rule: str,
    ):
        return self.api.register(rule, self.version)
