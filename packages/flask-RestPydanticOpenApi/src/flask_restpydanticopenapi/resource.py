from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar, cast

from annotationlib import get_annotations
from flask import Response, current_app, jsonify, make_response, request
from flask.views import MethodView
from pydantic import BaseModel, ValidationError
from pydantic_core import ErrorDetails


# addapted from flask-pydantic core.py
def make_json_response(
    content: BaseModel,
    status_code: int,
    by_alias: bool,
    exclude_none: bool = False,
) -> Response:
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


class Resource(MethodView):
    init_every_request = False  # pyright: ignore[reportUnannotatedClassAttribute]

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
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | Response:
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
