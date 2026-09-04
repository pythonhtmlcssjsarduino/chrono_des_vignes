from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from inspect import unwrap
from typing import Any

from pydantic import BaseModel

from flask_restpydanticopenapi.resource import Resource


@dataclass
class OpenApiMeta:
    """Class to hold OpenAPI metadata for a Resource class."""

    docs: dict[int, list[str]] = field(default_factory=lambda: defaultdict(list))
    responses: dict[str, dict[str, BaseModel]] = field(
        default_factory=lambda: defaultdict(dict)
    )


def get_meta_obj[**P, R](obj: type[Resource] | Callable[P, R]):
    """Get the meta object from a Resource class or instance."""
    if not hasattr(obj, "__openapi_meta__"):
        if hasattr((unwrapped := unwrap(obj)), "__openapi_meta__"):  # pyright: ignore[reportAny]
            meta: Any = getattr(unwrapped, "__openapi_meta__")  # noqa: B009  # pyright: ignore[reportAny]
        else:
            meta = OpenApiMeta()
            setattr(unwrapped, "__openapi_meta__", meta)  # noqa: B010  # pyright: ignore[reportAny]
    else:
        meta = getattr(obj, "__openapi_meta__")  # noqa: B009  # pyright: ignore[reportAny]
    if not isinstance(meta, OpenApiMeta):
        raise TypeError(
            f"__openapi_meta__ attribute of {obj} is not an OpenApiMeta instance."
        )
    return meta


def add_doc_to_meta[**P, R](
    obj: type[Resource] | Callable[P, R], doc: str, priority: int = 10
) -> None:
    """Add a doc string to the meta object of a Resource class or instance."""
    meta = get_meta_obj(obj)
    meta.docs[priority].append(doc)
