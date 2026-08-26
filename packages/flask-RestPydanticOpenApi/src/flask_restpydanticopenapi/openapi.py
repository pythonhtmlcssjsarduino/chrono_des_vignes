import inspect
import re
from collections.abc import Callable, Collection, Sequence
from typing import Annotated, Any, cast, get_args, get_origin
from warnings import warn

from annotationlib import Format, get_annotations
from openapi_pydantic import (
    DataType,
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
from werkzeug.routing import BaseConverter

from flask_restpydanticopenapi.resource import Resource
from flask_restpydanticopenapi.utils import generate_url, get_path_params_from_rule


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

    def __init__(self, converters: dict[str, type[BaseConverter]]) -> None:
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
