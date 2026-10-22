from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import NoReturn, cast

import click
from flask import Flask, Response, abort, current_app, send_from_directory

from flask_restpydanticopenapi.authorize import ResultAcces, Scope
from flask_restpydanticopenapi.openapi import OpenApiBuilder
from flask_restpydanticopenapi.resource import Resource
from flask_restpydanticopenapi.utils import generate_url


@click.command("openapi-export")
@click.option("-o", "--output", type=click.Path(dir_okay=False), default="openapi.json")
def openapi_export(output: str) -> None:
    """Exporte la spécification OpenAPI dans un fichier JSON."""
    api = current_app.extensions.get("flask_restpydanticopenapi")
    if not isinstance(api, Api):
        raise click.UsageError("Api is not initialized on this app")
    spec = api.get_openapi_spec()
    path = Path(output)
    path.write_text(spec + "\n", encoding="utf-8")
    click.echo(f"OpenAPI spec written to {path.resolve()}")


class Api:
    _app: Flask | None = None

    def __init__(self, app: Flask | None = None, api_prefix: str = "/api") -> None:
        self._pending: list[tuple[type[Resource], str, int]] = []
        if app is not None:
            self.init_app(app, api_prefix)

    def init_app(
        self,
        app: Flask,
        api_prefix: str = "/api",
    ) -> None:
        self.api_prefix: str = api_prefix  # pyright: ignore[reportUninitializedInstanceVariable]
        self._app = app
        # "live" : construit en mémoire (dev) ; "file" : sert l'artefact (prod) ; "off"
        self._openapi_mode: str = cast(  # pyright: ignore[reportUninitializedInstanceVariable]
            str,
            app.config.get(  # pyright: ignore[reportUnknownMemberType]
                "OPENAPI_MODE", "live" if app.debug else "file"
            ),
        )
        self._spec_path: Path = Path(  # pyright: ignore[reportUninitializedInstanceVariable]
            cast(
                str,
                app.config.get(  # pyright: ignore[reportUnknownMemberType]
                    "OPENAPI_SPEC_PATH", Path(app.root_path) / "openapi.json"
                ),
            )
        )

        self._builder: OpenApiBuilder | None = (  # pyright: ignore[reportUninitializedInstanceVariable]
            OpenApiBuilder(app.url_map.converters)
            if self._openapi_mode == "live"
            else None
        )

        if self._openapi_mode == "file" and not self._spec_path.is_file():
            raise RuntimeError(  # fail-fast au boot, pas un 404 mystérieux plus tard
                f"OpenAPI spec not found at {self._spec_path}. "
                + "Run `flask openapi-export`."
            )
        if self._openapi_mode == "live" and len(self._pending) != 0:
            for cls, rule, version in self._pending:
                self._add_resource(cls, rule, version)
            self._pending.clear()

        app.cli.add_command(openapi_export)

        app.extensions["flask_restpydanticopenapi"] = self
        if self._openapi_mode != "off":
            app.add_url_rule(
                f"{api_prefix}/swagger.json", "swagger", self._serve_openapi
            )

    def _serve_openapi(self):
        if self._builder is not None:  # dev : spec live
            return Response(
                self._builder.get_openapi_spec(), mimetype="application/json"
            )
        # prod : l'artefact figé, avec ETag/Last-Modified gratuits
        return send_from_directory(
            self._spec_path.parent,
            self._spec_path.name,
            mimetype="application/json",
        )

    def register[T: type[Resource]](self, rule: str, version: int) -> Callable[[T], T]:
        def decorator(cls: T):

            self._add_resource(cls, rule, version)
            return cls

        return decorator

    def _add_resource(self, cls: type[Resource], rule: str, version: int) -> None:
        if self._app is None:
            self._pending.append((cls, rule, version))
        else:
            self._app.add_url_rule(
                generate_url(rule, version, self.api_prefix),
                view_func=cls.as_view(f"v{version}_{cls.__name__.lower()}"),
            )
            if self._builder is not None:
                self._builder.add_resource(cls, rule, version, self.api_prefix)

    def version(self, version: int) -> ApiVersion:
        return ApiVersion(version, self)

    def get_openapi_spec(self):
        if self._builder is None:
            raise RuntimeError(
                "OpenApiBuilder is not initialized. Make sure the app is in debug mode."
            )
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
