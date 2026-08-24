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
import re
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass
from functools import wraps
from typing import Annotated, Any, ParamSpec, TypeVar, cast, get_args, get_origin
from warnings import warn

from annotationlib import Format, get_annotations
from flask import Flask, current_app, make_response, request, jsonify
from flask import Response as FlaskResponse
from flask.views import MethodView
from flask_swagger_ui import get_swaggerui_blueprint
from pydantic import ValidationError
from openapi_pydantic import (
    DataType,
    Example,
    Info,
    MediaType,
    OpenAPI,
    Operation,
    Parameter,
    PathItem,
    Paths,
    Reference,
    RequestBody,
    Response,
    Responses,
    Schema,
)
from openapi_pydantic.util import PydanticSchema, construct_open_api_with_schema_class
from pydantic import BaseModel
from pydantic_core import ErrorDetails
from werkzeug.routing import BaseConverter


def generate_url(rule: str, version: int, api_prefix: str) -> str:
    return f"{api_prefix}/v{version}{rule}"


def get_path_params_from_rule(rule: str) -> dict[str, str]:
    """
    Extract path parameter names and their converter types from a Flask/Werkzeug rule string.

    Args:
        rule: The URL rule string (e.g., "/user/<int:user_id>/<string:name>").

    Returns:
        A dictionary mapping parameter names to their converter types.
        Example: {"user_id": "int", "name": "string"}.
    """
    # Regex to match <converter:param_name> or <param_name>
    pattern = r"<(?:([^:>]+):)?([^>]+)>"
    matches: list[tuple[str, str]] = re.findall(pattern, rule)

    params: dict[str, str] = {}
    for converter, param_name in matches:
        # Default converter is 'string' if not specified
        params[param_name] = converter or "default"

    return params


def flask_rule_to_openapi_path(rule: str):
    """Convert a Flask/Werkzeug rule to an OpenAPI path.

    Examples:
        "/user/<int:user_id>/<name>" -> "/user/{user_id}/{name}"
    """
    # Replace occurrences like <converter:var> or <var> with {var}
    return re.sub(r"<(?:[^:>]+:)?([^>]+)>", r"{\1}", rule)


def annotation_to_data_type(annotation: Any) -> DataType:  # pyright: ignore[reportAny]
    """Convert a Python annotation into the matching OpenAPI `DataType`.

    Supports primitives, unions like `int | None`, and collection-like annotations.
    """
    if annotation is inspect._empty or annotation in (Any, object):  # pyright: ignore[reportPrivateUsage]
        return DataType.STRING
    if annotation is type(None):
        return DataType.NULL

    origin = get_origin(annotation)
    if origin is Annotated:
        args = get_args(annotation)
        if args:
            return annotation_to_data_type(args[0])

    if origin in (list, set, tuple, Sequence, Collection):
        return DataType.ARRAY
    if origin is dict:
        return DataType.OBJECT

    if origin is not None:
        args = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(args) == 1:
            return annotation_to_data_type(args[0])

    if annotation in (bool,):
        return DataType.BOOLEAN
    if annotation in (int,):
        return DataType.INTEGER
    if annotation in (float,):
        return DataType.NUMBER
    if annotation in (str, bytes, bytearray):
        return DataType.STRING
    if annotation in (dict,):
        return DataType.OBJECT
    if annotation in (list, tuple, set):
        return DataType.ARRAY

    if isinstance(annotation, str):
        normalized = annotation.lower()
        mapping = {
            "str": DataType.STRING,
            "string": DataType.STRING,
            "int": DataType.INTEGER,
            "integer": DataType.INTEGER,
            "float": DataType.NUMBER,
            "number": DataType.NUMBER,
            "bool": DataType.BOOLEAN,
            "boolean": DataType.BOOLEAN,
            "dict": DataType.OBJECT,
            "object": DataType.OBJECT,
            "list": DataType.ARRAY,
            "array": DataType.ARRAY,
            "tuple": DataType.ARRAY,
            "set": DataType.ARRAY,
            "none": DataType.NULL,
        }
        return mapping.get(normalized, DataType.STRING)

    return DataType.STRING


class OpenApiBuilder:
    _schema: str | None = None

    def __init__(self, api: Api, converters: dict[str, type[BaseConverter]]) -> None:
        self.api: Api = api
        self.converters: dict[str, type[BaseConverter]] = converters
        self.paths: Paths = {}
        self.types: dict[str, type[BaseModel]] = {}

    def add_resource[T: type[Resource]](
        self, cls: T, rule: str, version: int, api_prefix: str
    ) -> None:

        path_params = get_path_params_from_rule(rule)

        if cls.methods is None:
            return
        operations = {
            method.lower(): self._build_operation(
                cast(Callable[..., Any], getattr(cls, method.lower())), path_params
            )
            for method in cls.methods
        }

        summary, description = self._parse_sumary_and_description(cls)
        path_item = PathItem(summary=summary, description=description)

        for method_name, operation in operations.items():
            setattr(path_item, method_name, operation)

        self.paths[
            generate_url(flask_rule_to_openapi_path(rule), version, api_prefix)
        ] = path_item

    def _build_operation(
        self, fnc: Callable[..., Any], path_params: dict[str, str]
    ) -> Operation:

        summary, description = self._parse_sumary_and_description(fnc)
        return Operation(
            summary=summary,
            description=description,
            responses=self._build_operation_responses(fnc),
            parameters=list(self._build_operation_parameters(fnc, path_params)),
            deprecated=hasattr(fnc, "__deprecated__"),
            requestBody=self._build_operation_body(fnc),
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

        # Add 400 validation error response if function has query or body params
        annotations = get_annotations(fnc, eval_str=True)
        if annotations.get("query") is not None or annotations.get("body") is not None:
            responses["400"] = Response(
                description="Validation error",
                content={
                    "application/json": MediaType(
                        schema=PydanticSchema(schema_class=ValidationErrorResponse)
                    )
                },
            )

        return responses

    def _build_operation_parameters(
        self, fnc: Callable[..., Any], path_params: dict[str, str]
    ) -> list[Parameter | Reference]:
        params: list[Parameter | Reference] = []

        signature = inspect.signature(fnc)
        annotations = get_annotations(fnc, eval_str=True)

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
                + f"Default: {param.default}, "
                + f"Annotation: {param.annotation}, "
            )

        # path param
        # -> presents dans la rule
        sign_params = signature.parameters.copy()
        sign_params.pop("self")
        unfound_names = set[str]()
        for name in path_params:
            param = sign_params.pop(name, None)
            if param is None:
                unfound_names.add(name)
                continue
            schema_type = annotation_to_data_type(param.annotation)
            params.append(
                Parameter(
                    name=name,
                    param_in="path",  # pyright: ignore[reportCallIssue]
                    required=param.default is param.empty,
                    schema=Schema(
                        type=schema_type,
                        default=param.default
                        if param.default is not param.empty
                        else None,
                    ),
                )
            )

        query_model_fields = (
            query.model_fields
            if sign_params.get("query") is not None
            and issubclass((query := annotations["query"]), BaseModel)
            else {}
        )
        for name in unfound_names:
            param = query_model_fields.pop(name, None)
            if param is None:
                warn(
                    f'the parameter "{name}" present in the rule is not present in the main view signature nor the query object this will raise an error at call time!',
                    stacklevel=6,
                )
                continue
            params.append(
                Parameter(
                    name=name,
                    param_in="path",  # pyright: ignore[reportCallIssue]
                    required=param.is_required(),
                    schema=Schema(
                        type=annotation_to_data_type(param.annotation),
                        default=param.annotation,
                    ),
                )
            )
        # query param

        for name, param in sign_params.items():
            if name in ("query", "form", "body", "return"):
                continue
            schema_type = annotation_to_data_type(param.annotation)
            params.append(
                Parameter(
                    name=name,
                    param_in="query",  # pyright: ignore[reportCallIssue]
                    required=param.default is param.empty,
                    schema=Schema(
                        type=schema_type,
                        default=param.default
                        if param.default is not param.empty
                        else None,
                    ),
                )
            )

        for name, param in query_model_fields.items():
            schema_type = annotation_to_data_type(param.annotation)
            params.append(
                Parameter(
                    name=name,
                    param_in="query",  # pyright: ignore[reportCallIssue]
                    required=param.is_required(),
                    schema=Schema(type=schema_type, default=param.annotation),
                )
            )

        return params

    def _build_operation_body(
        self,
        fnc: Callable[..., Any],
    ) -> RequestBody | None:
        annotations = get_annotations(fnc, eval_str=True)
        print("oppp body ", annotations)
        # body param
        if (body := annotations.get("body")) is not None and issubclass(
            body, BaseModel
        ):
            return RequestBody(
                content={
                    "application/json": MediaType(
                        schema=PydanticSchema(schema_class=body)
                    )
                }
            )

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
        if self._schema is not None:
            return self._schema
        # create an OpenAPI model to validate structure
        openapi = OpenAPI(
            openapi="3.1.1",
            info=Info(title="Chrono Des Vignes API", version="1.0.0"),
            paths=self.paths,
        )

        openapi = construct_open_api_with_schema_class(openapi)
        self._schema = openapi.model_dump_json(
            by_alias=True, exclude_none=True, indent=2
        )
        return self._schema


class Api:
    def __init__(self, app: Flask | None = None, api_prefix: str = "/api") -> None:
        if app is not None:
            self.init_app(app, api_prefix)

    def init_app(self, app: Flask, api_prefix: str = "/api") -> None:
        self._builder: OpenApiBuilder = OpenApiBuilder(self, app.url_map.converters)  # pyright: ignore[reportUninitializedInstanceVariable]
        self.api_prefix: str = api_prefix  # pyright: ignore[reportUninitializedInstanceVariable]
        self._app: Flask = app  # pyright: ignore[reportUninitializedInstanceVariable]

        @app.route(f"{api_prefix}/swagger.json")
        def swagger():
            return FlaskResponse(self.get_openapi_spec(), mimetype="application/json")

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
    ):
        return self.api.register(rule, self.version)


@dataclass
class apiData:
    api_version: int
    api_rule: str


# addapted from flask-pydantic core.py
def make_json_response(
    content: BaseModel,
    status_code: int,
    by_alias: bool,
    exclude_none: bool = False,
) -> FlaskResponse:
    """serializes model, creates JSON response with given status code"""
    js = content.model_dump_json(exclude_none=exclude_none, by_alias=by_alias)
    response = make_response(js, status_code)
    response.mimetype = "application/json"
    return response


# Helper functions for parameter parsing (inspired by flask-pydantic)
def _sanitize_validation_errors(errors: list[ErrorDetails]) -> list[dict[str, Any]]:
    """Convert Pydantic ErrorDetails to JSON-serializable dictionaries.

    Replaces exception instances in error context with serializable representations
    of their type and message.
    """
    sanitized: list[dict[str, Any]] = []

    for error in errors:
        # Convert ErrorDetails (TypedDict) to mutable dict
        error_dict = dict(error)

        # Sanitize the context field if it contains exceptions
        ctx = error_dict.get("ctx")
        if isinstance(ctx, dict):
            error_obj = ctx.get("error")
            if isinstance(error_obj, Exception):
                # Replace exception with JSON-serializable dict
                ctx["error"] = {
                    "type": type(error_obj).__name__,
                    "message": str(error_obj),
                }

        sanitized.append(error_dict)

    return sanitized


def _parse_query_params(
    query_model: type[BaseModel] | None,
) -> tuple[BaseModel | None, dict[str, Any] | None]:
    """Parse and validate query parameters from Flask request.

    Returns:
        Tuple of (parsed_model, errors_dict or None)
    """
    if query_model is None:
        return None, None

    try:
        # Convert werkzeug ImmutableMultiDict to dict, handling multiple values
        query_dict = request.args.to_dict(flat=True)
        return query_model(**query_dict), None
    except ValidationError as ve:
        return None, {"query_params": _sanitize_validation_errors(ve.errors())}


def _parse_body(
    body_model: type[BaseModel] | None,
) -> tuple[BaseModel | None, dict[str, Any] | None]:
    """Parse and validate request body from JSON.

    Returns:
        Tuple of (parsed_model, errors_dict or None)
    """
    if body_model is None:
        return None, None

    try:
        data = request.get_json(silent=True)
        if data is None:
            data = {}
        return body_model(**data), None
    except ValidationError as ve:
        return None, {"body_params": _sanitize_validation_errors(ve.errors())}


P = ParamSpec("P")
R = TypeVar("R")


class ValidationErrorDetail(BaseModel):
    """Individual validation error detail from Pydantic"""

    loc: tuple[str | int, ...]
    "Location path to the field that failed validation (e.g., ('name', 0, 'age'))"

    msg: str
    "The validation error message"

    type: str
    "Error type (e.g., 'value_error', 'type_error', 'missing')"

    ctx: dict[str, Any] | None = None
    "Optional context with additional error information"


class ValidationErrorResponse(BaseModel):
    """OpenAPI schema for validation error responses"""

    validation_error: dict[str, list[ValidationErrorDetail]]
    "Validation errors grouped by source: 'query_params' or 'body_params'"


class Resource(MethodView):
    init_every_request = False  # pyright: ignore[reportUnannotatedClassAttribute]
    __api_data__: apiData | None = None

    response_by_alias: bool = False
    "whether Pydantic's alias is used"
    exclude_none: bool = False
    "whether to remove None fields from response"
    on_success_status: int = 200

    @classmethod
    def _method_decorator(cls, func: Callable[P, R]):

        # Extract annotations once at decorator time
        annotations = get_annotations(func, eval_str=True)
        query_model = annotations.get("query")
        body_model = annotations.get("body")

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | FlaskResponse:
            # Parse parameters and collect errors in a single pass
            query_params, query_errors = _parse_query_params(query_model)
            body_params, body_errors = _parse_body(body_model)

            # Collect all validation errors
            errors: dict[str, Any] = {}
            if query_errors:
                errors.update(query_errors)
            if body_errors:
                errors.update(body_errors)

            # Return error response if validation failed
            if errors:
                return make_response(jsonify({"validation_error": errors}), 400)

            # Inject parsed parameters into kwargs
            if query_params is not None:
                kwargs["query"] = query_params
            if body_params is not None:
                kwargs["body"] = body_params

            res = cast(R, current_app.ensure_sync(func)(*args, **kwargs))

            if isinstance(res, BaseModel):
                return make_json_response(
                    res, cls.on_success_status, cls.response_by_alias, cls.exclude_none
                )
            elif (
                isinstance(res, tuple)
                and len(res) in [2, 3]  # pyright: ignore[reportUnknownArgumentType]
                and isinstance(res[0], BaseModel)
            ):  # with return code and/or headers
                headers = None
                status = cls.on_success_status
                if isinstance(res[1], (dict, tuple, list)):
                    headers = res[1]
                elif len(res) == 3 and isinstance(res[2], (dict, tuple, list)):
                    status = res[1]
                    headers = res[2]
                else:
                    status = res[1]

                ret = make_json_response(
                    res[0], status, cls.response_by_alias, cls.exclude_none
                )

                if headers:
                    ret.headers.update(headers)
                return ret
            return res

        return wrapper

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)

        if cls.methods is None:
            return
        for method in cls.methods:
            fnc = cast(Callable[..., Any], getattr(cls, method.lower()))
            setattr(cls, method.lower(), cls._method_decorator(fnc))


if __name__ == "__main__":
    app = Flask(__name__)
    api = Api(app)

    swaggerui_blueprint = get_swaggerui_blueprint(
        "",  # Swagger UI static files will be mapped to '{SWAGGER_URL}/dist/'
        "http://localhost:5000/api/swagger.json",
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

    v1 = api.version(1)

    class GetResponse(BaseModel):
        id: int
        name: int

    class PutJson(BaseModel):
        id: int
        name: str

    class PutBody(BaseModel):
        what: str
        how_many: int

    @v1.register("/test/<int:name>")
    class test(Resource):
        """hello world
        its me"""

        def get(self, name: int, id: int = 3) -> GetResponse:
            """this is my func docstring

            that is a description
            ---
            this will not show on the swager"""
            return GetResponse(id=2, name=name)

        def put(self, name: int, body: PutBody) -> PutJson:
            return PutJson(id=2, name="bob")

    @v1.register("/hello")
    class hello(Resource):
        "hey"

        def delete(self) -> PutJson:
            return PutJson(id=2, name="bob")

    print(api.get_openapi_spec())
    print(app.test_client().get("/api/v1/test/76").text)
    # app.run(debug=True)
