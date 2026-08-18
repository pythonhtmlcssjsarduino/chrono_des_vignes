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

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypedDict, cast

from annotationlib import Format, get_annotations
from flask import Flask
from flask import Response as FlaskResponse
from flask.views import MethodView
from flask_swagger_ui import (
    get_swaggerui_blueprint,  # pyright: ignore[reportUnknownVariableType]
)
from openapi_pydantic import (
    Info,
    MediaType,
    OpenAPI,
    Operation,
    Parameter,
    PathItem,
    Paths,
    Response,
    Responses,
)
from openapi_pydantic.util import PydanticSchema, construct_open_api_with_schema_class
from pydantic import BaseModel

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
        self.paths: Paths = {}
        self.types: dict[str, type[BaseModel]] = {}

    def add_resource[T: type[Resource]](
        self, cls: T, rule: str, version: int, api_prefix: str
    ) -> None:

        assert cls.methods
        operations = {
            method.lower(): self._build_operation(
                cast(Callable[..., Any], getattr(cls, method.lower()))
            )
            for method in cls.methods
        }

        summary, description = self._parse_sumary_and_description(cls)
        path_item = PathItem(summary=summary, description=description)

        for method_name, operation in operations.items():
            setattr(path_item, method_name, operation)

        self.paths[generate_url(rule, version, api_prefix)] = path_item

    def _build_operation(self, fnc: Callable[..., Any]) -> Operation:

        summary, description = self._parse_sumary_and_description(fnc)
        self._build_operation_responses(fnc)
        print(self._build_operation_parameters(fnc))
        return Operation(
            summary=summary,
            description=description,
            responses=self._build_operation_responses(fnc),
            deprecated=hasattr(fnc, "__deprecated__"),
        )

    def _build_operation_responses(self, fnc: Callable[..., Any]) -> Responses:
        responses: Responses = {}

        return_annotation: Any | None = get_annotations(
            fnc, eval_str=True, format=Format.VALUE
        ).get("return")
        if return_annotation is None:
            responses["200"] = Response(description="OK")
        else:
            responses["200"] = Response(
                description="OK",
                content={
                    "application/json": MediaType(
                        schema=PydanticSchema[Any](
                            schema_class=return_annotation  # pyright: ignore[reportAny]
                        )
                    )
                },
            )

        return responses

    def _build_operation_parameters(self, fnc: Callable[..., Any]) -> list[Parameter]:
        params: list[Parameter] = []

        signature = inspect.signature(fnc)

        print(
            fnc.__name__,
            fnc.__annotations__,
            fnc.__annotate__,
            fnc.__defaults__,
            fnc.__kwdefaults__,
            fnc.__type_params__,
        )
        for name, param in signature.parameters.items():
            print(
                f"Name: {name}, "
                f"Default: {param.default}, "
                + f"Annotation: {param.annotation}, "
                + f"Kind: {param.kind.name}"
            )

        return params

    def _parse_sumary_and_description(self, fnc: Callable[..., Any] | type[Resource]):
        doc = fnc.__doc__.strip() if fnc.__doc__ else ""
        doc = doc.split(sep="---")[0]  # Only take the part before '---' for summary
        docs = doc.split("\n", 1)
        if len(docs) == 2:
            (summary, description) = docs
        else:
            summary = docs[0]
            description = ""

        return summary.strip(), description.strip()

    def get_openapi_spec(self) -> str:
        # create an OpenAPI model to validate structure
        openapi = OpenAPI(
            openapi="3.1.1",
            info=Info(title="Chrono Des Vignes API", version="1.0.0"),
            paths=self.paths,
        )

        openapi = construct_open_api_with_schema_class(openapi)
        return openapi.model_dump_json(by_alias=True, exclude_none=True, indent=2)


class Api:
    def __init__(self, app: Flask | None = None, api_prefix: str = "/api") -> None:
        self._builder: OpenApiBuilder = OpenApiBuilder(self)
        if app is not None:
            self.init_app(app, api_prefix)

    def init_app(self, app: Flask, api_prefix: str = "/api") -> None:
        self.api_prefix: str = api_prefix  # pyright: ignore[reportUninitializedInstanceVariable]
        self._app: Flask = app  # pyright: ignore[reportUninitializedInstanceVariable]

        @app.route(f"{api_prefix}/swagger.json")
        def swagger():
            return FlaskResponse(self.get_openapi_spec(), mimetype="application/json")

        swaggerui_blueprint = get_swaggerui_blueprint(
            api_prefix,  # Swagger UI static files will be mapped to '{SWAGGER_URL}/dist/'
            f"{app.config['SERVER_NAME'] or 'http://localhost:5000'}{api_prefix}/swagger.json",
            config={  # Swagger UI config overrides
                "app_name": "Test application"
            },
            # oauth_config={  # OAuth config. See https://github.com/swagger-api/swagger-ui#oauth2-configuration .
            #    'clientId': "your-client-id",
            #    'clientSecret': "your-client-secret-if-required",
            #    'realm': "your-realms",
            #    'appName': "your-app-name",
            #    'scopeSeparator': " ",
            #    'additionalQueryStringParams': {'test': "hello"}
            # }
        )
        app.register_blueprint(swaggerui_blueprint)

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

    v1 = api.version(1)

    class GetResponse(BaseModel):
        id: int
        name: str

    class PutJson(BaseModel):
        id: int
        name: str

    @v1.register("/test")
    class test(Resource):
        """hello world
        its me"""

        def get(self, name="hello", id: int = 3) -> GetResponse:
            """this is my func docstring

            that is a description
            ---
            this will not show on the swager"""
            return GetResponse(id=2, name="bob")

        def put(self) -> GetResponse:
            return GetResponse(id=2, name="bob")

    print(api.get_openapi_spec())
    app.run(debug=True)
