from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any, ClassVar


@dataclass
class ScopeResponse:
    """Response model for scope authorization."""

    authorized: bool
    message: str | None = None


OK = ScopeResponse(authorized=True)


class BaseScope(ABC):
    """Base class for all scops."""

    name: ClassVar[str]
    parents: ClassVar[list[BaseScope]]

    def __init_subclass__(
        cls, name: str | None = None, parents: list[BaseScope] | BaseScope | None = None
    ) -> None:
        cls.name = name or cls.__name__.lower()
        cls.parents = (
            parents if isinstance(parents, list) else ([parents] if parents else [])
        )
        return super().__init_subclass__()

    @abstractmethod
    def authorize(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> ScopeResponse:
        """Authorize the request."""
        raise NotImplementedError

    def check(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> ScopeResponse:
        for parent in self.parents:
            resp = parent.check(args, kwargs)
            if not resp.authorized:
                return resp

        return self.authorize(args, kwargs)

    def __call__[T: Callable[..., Any]](self, f: T):

        @wraps(f)
        def wrapped_function(*args: Any, **kwargs: Any) -> Any:

            # Call the authorize method to check if the request is authorized
            response = self.authorize(args, kwargs)

            if not response.authorized:
                return {"message": response.message or "Unauthorized"}, 403

            return f(*args, **kwargs)

        return wrapped_function
