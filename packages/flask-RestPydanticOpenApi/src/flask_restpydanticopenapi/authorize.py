from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, cast

__all__ = [
    "DENIED",
    "OK",
    "ResultAcces",
    "Scope",
    "ScopeFactory",
    "ScopeResponse",
    "scope_it",
]


class _ScopeFactoryIn(Protocol):
    def authorize(self, args: Any, kwargs: Any) -> ScopeResponse:  # pyright: ignore[reportAny]
        ...


class _ScopeFactoryResult(Protocol):
    def authorize_result(self, result: object) -> ResultAcces: ...


class _ScopeFactoryBoth(_ScopeFactoryIn, _ScopeFactoryResult, Protocol):
    pass


type ScopeFactory = _ScopeFactoryBoth | _ScopeFactoryIn | _ScopeFactoryResult


class Scope(Protocol):
    name: str
    depends_on: list[Scope]
    description: str

    def authorize(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> ScopeResponse:
        """authorize the acces to the route (called before the execution of the route)
        if all scopes are linked with and -> all scope must be ok to run the request"""
        ...

    def authorize_result(self, result: object) -> ResultAcces:
        """validate the access of a resource ( the result arg ) only one scope need to validate it to be validated"""
        ...


def _default_ok(*arg: Any, **kwargs: Any):  # pyright: ignore[reportAny, reportUnusedParameter]
    return OK


def _default_denied(result: object):  # pyright: ignore[reportUnusedParameter]
    return ResultAcces.unknown


def scope_it(
    depends_on: list[Scope] | Scope | None = None,
    name: str | None = None,
    description: str | None = None,
):

    def decorator(cls: type[ScopeFactory]) -> Scope:
        instance = cast(Scope, cls())

        instance.name = name if name is not None else cls.__name__
        instance.depends_on = (
            depends_on
            if isinstance(depends_on, list)
            else ([depends_on] if depends_on else [])
        )
        instance.description = (
            description if description else cls.__doc__ or ""
        ).strip()

        if not hasattr(instance, "authorize"):
            instance.authorize = _default_ok

        if not hasattr(instance, "authorize_result"):
            instance.authorize_result = _default_denied

        return instance

    return decorator


@dataclass(frozen=True, slots=True)
class ScopeResponse:
    """Response model for scope authorization."""

    authorized: bool
    message: str | None = None

    def __call__(self, message: str):
        return ScopeResponse(authorized=self.authorized, message=message)


OK = ScopeResponse(authorized=True)
DENIED = ScopeResponse(authorized=False)


class ResultAcces(Enum):
    read_write = 3
    read_only = 2
    denied = 1
    unknown = 0
