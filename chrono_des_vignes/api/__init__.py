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
# See the GNU General Public License for more fcdetails.
# You should have received a copy of the GNU General Public License along with Chrono des vignes.
# If not, see <https://www.gnu.org/licenses/>.
#
# You may contact me at chrono-des-vignes@ikmail.com
# or from my github https://github.com/pythonhtmlcssjsarduino/chrono_des_vignes
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypedDict, cast

from annotationlib import Format, get_annotations
from flask import Flask
from flask.views import MethodView
from pydantic import BaseModel
from pydantic.json_schema import models_json_schema

# Source - https://stackoverflow.com/a/76646986
# Posted by pradyunsg
# Retrieved 2026-08-17, License - CC BY-SA 4.0

type JSON = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None
type ModelName = str


def generate_url(rule: str, version: int, api_prefix: str) -> str:
    return f"{api_prefix}/v{version}{rule}"


class OpenApiResponseTypings(TypedDict):
    description: str
    model: ModelName | None


class OpenApiMethodTypings(TypedDict):
    summary: str
    description: str
    parameters: list[ModelName]
    responses: dict[int, OpenApiResponseTypings]


class OpenApiResourceTypings(TypedDict):
    resource: type[Resource]
    methods: dict[str, OpenApiMethodTypings]


class OpenApiBuilder:
    def __init__(self, api: Api) -> None:
        self.api: Api = api
        self.paths: dict[
            tuple[str, int, str],
            OpenApiResourceTypings,
        ] = {}
        self.types: dict[str, type[BaseModel]] = {}

    def add_resource[T: type[Resource]](
        self, cls: T, rule: str, version: int, api_prefix: str
    ) -> None:
        self.paths[(api_prefix, version, rule)] = {"resource": cls, "methods": {}}
        self._parse_resource_types(cls)

    def _parse_resource_types(self, cls: type[Resource]) -> None:
        assert cls.methods
        api_data = cls.__api_data__
        assert api_data

        methods_types = self.paths[
            (self.api.api_prefix, api_data.api_version, api_data.api_rule)
        ]["methods"]
        for method in cls.methods:
            fnc = cast(Callable[..., Any], getattr(cls, method.lower()))
            methods_types[method.lower()] = {
                "summary": "",
                "description": "",
                "parameters": [],
                "responses": {},
            }
            self._parse_method_types(
                fnc,
                methods_types[method.lower()],
            )

    def _parse_method_types(
        self, fnc: Callable[..., Any], method_type: OpenApiMethodTypings
    ) -> None:
        print(
            fnc.__name__,
            fnc.__annotations__,
            fnc.__annotate__,
            fnc.__defaults__,
            fnc.__kwdefaults__,
            fnc.__type_params__,
        )
        # get the return type -> 200 OK
        return_ = get_annotations(fnc, eval_str=True, format=Format.VALUE).get("return")
        if return_ and hasattr(return_, "model_json_schema"):
            print(return_.model_json_schema())

    def _build_components(self) -> JSON:
        _, schemas = models_json_schema(
            [(model, "validation") for model in self.types.values()],
            ref_template="#/components/schemas/{model}",
        )
        print(_)
        return {
            "schemas": schemas.get("$defs", {}),
        }

    def _build_method_item(self, fnc: Callable[..., Any]) -> JSON:
        doc = fnc.__doc__.strip() if fnc.__doc__ else ""
        doc = doc.split("---")[0]  # Only take the part before '---' for summary
        docs = doc.split("\n\n", 1)
        if len(docs) == 2:
            (summary, description) = docs
        else:
            summary = docs[0]
            description = ""

        return {
            "summary": summary,
            "description": description,
            "parameters": [],
            "responses": {},
        }

    def _build_path_item(self, cls: type[Resource]):
        assert cls.methods

        return {
            method.lower(): self._build_method_item(
                cast(Callable[..., Any], getattr(cls, method.lower()))
            )
            for method in cls.methods
        }

    def get_openapi_spec(self) -> JSON:
        return {
            "openapi": "3.1.0",
            "info": {
                "title": "Chrono Des Vignes API",
                "version": "1.0.0",
            },
            "paths": {
                generate_url(rule, version, api_prefix): self._build_path_item(
                    resource_type["resource"]
                )
                for (api_prefix, version, rule), resource_type in self.paths.items()
            },
            "components": self._build_components(),
        }


class Api:
    def __init__(self, app: Flask | None = None, api_prefix: str = "/api") -> None:
        self._builder: OpenApiBuilder = OpenApiBuilder(self)
        if app is not None:
            self.init_app(app, api_prefix)

    def init_app(self, app: Flask, api_prefix: str = "/api") -> None:
        self.api_prefix: str = api_prefix  # pyright: ignore[reportUninitializedInstanceVariable]
        self._app: Flask = app  # pyright: ignore[reportUninitializedInstanceVariable]

    def register[T: type[Resource]](self, rule: str, version: int) -> Callable[[T], T]:
        def decorator(cls: T):

            self._add_resource(cls, rule, version)
            return cls

        return decorator

    def _add_resource[T: type[Resource]](self, cls: T, rule: str, version: int) -> None:
        self._app.add_url_rule(
            generate_url(rule, version, self.api_prefix),
            view_func=cls.as_view(f"v{version}_{cls.__name__.lower()}"),
        )
        cls.__api_data__ = apiData(version, rule)
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
    ) -> Callable[[T], T]:
        return self.api.register(rule, self.version)


@dataclass
class apiData:
    api_version: int
    api_rule: str


class Resource(MethodView):
    init_every_request = False  # pyright: ignore[reportUnannotatedClassAttribute]
    __api_data__: apiData | None = None


if __name__ == "__main__":
    app = Flask(__name__)
    api = Api(app)

    apiv1 = api.version(1)

    class GetResponse(BaseModel):
        id: int
        name: str

    class PutJson(BaseModel):
        id: int
        name: str

    @apiv1.register("/test")
    class test(Resource):
        """hello world

        its me"""

        def get(self) -> GetResponse:
            "this is my func docstring"
            return GetResponse(id=2, name="bob")

        def put(self):
            return {}

    print(json.dumps(api.get_openapi_spec(), indent=4))
    # app.run(debug=True)
