from __future__ import annotations

import inspect
import typing
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    cast,
    final,
    override,
)

from flask import current_app
from pydantic import Field
from pydantic.annotated_handlers import GetJsonSchemaHandler
from pydantic.json_schema import SkipJsonSchema
from pydantic_core import CoreSchema, PydanticOmit

if TYPE_CHECKING:
    from flask_restpydanticopenapi.api import Api
from flask_restpydanticopenapi.authorize import ResultAcces, Scope

__all__ = [
    "Body",
    "ScopeSet",
    "internal_getter",
]

"""extracted from pydantic.json_schema.SkipJsonSchema"""
if TYPE_CHECKING:
    type Internal[T: Any] = SkipJsonSchema[Annotated[T, ...]]
else:

    @dataclass(slots=True)
    class Internal[T: any]:
        def __class_getitem__(cls, item: T) -> T:
            return Annotated[item, cls()]

        def __get_pydantic_json_schema__(
            self, core_schema: CoreSchema, handler: GetJsonSchemaHandler
        ) -> dict[str, Any]:
            raise PydanticOmit

        def __hash__(self) -> int:
            return hash(type(self))


_UNSET: Any = object()


@final
class Body[T]:
    """Référence typée vers un champ du body de la requête.

    ``T`` est le type **attendu** de la valeur du champ référencé : il doit
    correspondre à l'annotation du champ dans le modèle pydantic.

    - à la déclaration (dans le modèle) : ``Body("id")`` — seul ``name`` compte,
      ``T`` est inféré depuis la signature du getter (ou explicite : ``Body[int]("id")``) ;
    - au runtime (dans le getter)    : ``value`` contient ``data[name]``, typé ``T``.
    """

    __slots__ = ("name", "value")

    value: T  # injecté au runtime par le décorateur, jamais lu avant

    def __init__(self, name: str) -> None:
        self.name = name
        self.value = cast("T", _UNSET)

    @override
    def __repr__(self) -> str:
        return f"Body({self.name!r})"


def _bind[T](ref: Body[T], value: Any) -> Body[T]:  # pyright: ignore[reportAny]
    """Copie de `ref` avec la valeur lue dans le body injectée."""
    bound = Body[T](ref.name)
    bound.value = value
    return bound


class ScopeSet(set[Scope]):
    def _flatten_scope(self, scope: Scope):
        scopeset = ScopeSet({scope})
        for depend in scope.depends_on:
            scopeset.update(self._flatten_scope(depend))
        return scopeset

    def flattened(self) -> ScopeSet:
        scopeset = ScopeSet()
        for scope in self:
            if scope not in scopeset:
                scopeset.update(self._flatten_scope(scope))
        return scopeset

    def authorize_result(
        self, result: object
    ) -> tuple[ResultAcces, dict[Scope, ResultAcces]]:
        access_dict: dict[Scope, ResultAcces] = {}
        for scope in self.flattened():
            authorisation = scope.authorize_result(result)
            if authorisation != ResultAcces.unknown:
                access_dict[scope] = authorisation

        if len(access_dict) == 0:
            access = ResultAcces.read_write
        else:
            access = ResultAcces(max(v.value for v in access_dict.values()))

        return access, access_dict


def internal_getter[**P, R](
    scopes: list[Scope] | Scope | None = None,
) -> Callable[[Callable[P, R]], Callable[P, Internal[R]]]:
    """
    Le getter décoré doit n'accepter que des paramètres ``Body[...]``.
    Le wrapper retourné possède exactement la même signature (ParamSpec) :
    l'appel ``GetUser(id=Body("id"), what=Body("what"))`` est donc vérifié
    statiquement de bout en bout — noms des kwargs, types ``Body[...]``,
    paramètres manquants ou superflus.

    Au runtime, chaque ``Body`` est ré-résolu avec la valeur du champ du body
    avant l'appel du getter : ``id.value`` (typé ``T``) et ``id.name`` (``str``).
    """
    if scopes is None:
        scopes = []
    elif not isinstance(scopes, list):
        scopes = [scopes]
    scope_set = ScopeSet(scopes)

    def decorator(fnc: Callable[P, R]):
        signature = inspect.signature(fnc)

        # Garde-fou à l'import : tous les paramètres doivent être annotés Body[...].
        hints = typing.get_type_hints(fnc)
        for param in signature.parameters.values():
            hint = hints.get(param.name)
            if typing.get_origin(hint) is not Body and hint is not Body:
                raise TypeError(
                    f"@internal_multi_getter : le paramètre {param.name!r} de {fnc.__name__} doit être annoté Body[...], pas {hint!r}"
                )

        @wraps(fnc)
        def wrapper(*args: P.args, **kwargs: P.kwargs):
            bound = signature.bind(*args, **kwargs)
            refs: dict[str, Body[Any]] = dict(bound.arguments)

            def factory(data: dict[str, Any]) -> R:
                resolved: dict[str, Body[Any]] = {}
                for param_name, ref in refs.items():
                    if not isinstance(ref, Body):  # pyright: ignore[reportUnnecessaryIsInstance]
                        raise TypeError(
                            f"{fnc.__name__} : le paramètre {param_name!r} doit être un Body[...]"
                        )
                    try:
                        raw = data[ref.name]  # pyright: ignore[reportAny]
                    except KeyError:
                        raise KeyError(
                            f"{fnc.__name__} : le champ {ref.name!r} est absent du body"
                        ) from None
                    resolved[param_name] = _bind(ref, raw)
                result = cast(Callable[..., R], fnc)(**resolved)

                # check the authorization of the result
                access, access_dict = scope_set.authorize_result(result)

                api = cast("Api", current_app.extensions["flask_restpydanticopenapi"])

                match access:
                    case ResultAcces.read_write:
                        return result
                    case ResultAcces.read_only:
                        return api.result_as_read_only_callback(result)
                    case _:
                        api.result_acces_denied_callback(result, access_dict)

            # add the scopes to the factory so that the openapi builder can grab it
            field = Field(default_factory=factory)
            field.metadata.append(scope_set)  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
            field.metadata.append(Internal())  # pyright: ignore[reportCallIssue, reportUnknownMemberType, reportAttributeAccessIssue]
            return field

        return wrapper

    return decorator
