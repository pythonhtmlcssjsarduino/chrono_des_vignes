from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any


@dataclass
class ScopeResponse:
    """Response model for scope authorization."""

    authorized: bool
    message: str | None = None


OK = ScopeResponse(authorized=True)


class BaseScope(ABC):
    """Base class for all scops."""

    def __init__(self, name: str):
        self.name: str = name

    parents: list[BaseScope]

    @abstractmethod
    def authorize(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> ScopeResponse:
        """Authorize the request."""
        raise NotImplementedError

    def __call__[T: Callable[..., Any]](self, f: T):

        @wraps(f)
        def wrapped_function(*args: Any, **kwargs: Any) -> Any:

            # Call the authorize method to check if the request is authorized
            response = self.authorize(args, kwargs)

            if not response.authorized:
                return {"message": response.message or "Unauthorized"}, 403

            return f(*args, **kwargs)

        return wrapped_function
