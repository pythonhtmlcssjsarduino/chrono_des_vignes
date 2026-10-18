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

from pydantic.annotated_handlers import GetJsonSchemaHandler
from pydantic.json_schema import SkipJsonSchema
from pydantic_core import CoreSchema, PydanticOmit

from flask_restpydanticopenapi.api import Api
from flask_restpydanticopenapi.authorize import OK, BaseScope, ScopeResponse
from flask_restpydanticopenapi.resource import Resource

"""extracted from pydantic.json_schema.SkipJsonSchema"""
if TYPE_CHECKING:
    type Internal[T: Any] = SkipJsonSchema[Annotated[T, ...]]
else:

    @dataclass(slots=True)
    class Internal[T: any]:
        def __class_getitem__(cls, item: T) -> T:
            return Annotated[item, ...]

        def __get_pydantic_json_schema__(
            self, core_schema: CoreSchema, handler: GetJsonSchemaHandler
        ) -> dict[str, Any]:
            raise PydanticOmit

        def __hash__(self) -> int:
            return hash(type(self))


from flask import Flask
from flask_swagger_ui import get_swaggerui_blueprint
from pydantic import BaseModel, Field

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


@dataclass()
class User:
    id: int
    name: str


"""
class InternalBase[P, R](ABC):
    @abstractmethod
    def compute(cls, field: P, field_name: str) -> R:
        pass

    @classmethod
    def get(cls, model: dict[str, Any], field_name: str) -> R:
        instance = cls(field_name)

        if (field := model.get(field_name)) is None:
            raise ValueError(f"Field {field_name} not found in model")

        if not isinstance(field, cls.field_type):
            raise TypeError(
                f"Field {field_name} is not of type {cls.field_type.__name__}"
            )

        return instance.compute(field, field_name)

    def __init_subclass__(
        cls, field_type: type[P] | UnionType | None = None, **kwargs: Any
    ) -> None:  # pyright: ignore[reportAny]
        super().__init_subclass__(**kwargs)

        # If field_type is not provided, extract it from the type arguments
        if field_type is None:
            for base in cls.__orig_bases__:
                origin = get_origin(base)
                if origin is InternalBase or (
                    origin
                    and isinstance(origin, type)
                    and issubclass(origin, InternalBase)
                ):
                    args = get_args(base)
                    if args:
                        field_type = args[0]  # First type arg is P
                        break

        if field_type is None:
            raise ValueError(f"Could not determine field_type for {cls.__name__}")

        cls.field_type = field_type  # pyright: ignore[reportUnannotatedClassAttribute]

    def __new__(cls, field_name: str):
        return Field(default_factory=lambda data: cls.get(data, field_name))


class GetUser(InternalBase[int, User]):
    @override
    def compute(cls, field: int, field_name: str) -> User:
        return User(field, field_name)
"""

"""def internal_getter[**P, R]():

    def decorator(fnc: Callable[P, R]):
        @wraps(fnc)
        def wrapper(*args: P.args, **kwargs: P.kwargs):
            return fnc(*args, **kwargs)

        return wrapper

    return decorator"""


"""Getters multi-champs strictement typés.

Remplace `internal_getter` (mono-champ) par `internal_multi_getter` : le getter
peut lire autant de champs du body que nécessaire, avec un typage statique
de bout en bout (mypy / pyright en mode strict).
"""

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


def internal_getter[**P, R](fnc: Callable[P, R]):
    """Décorateur **sans parenthèses** : ``@internal_multi_getter``.

    Le getter décoré doit n'accepter que des paramètres ``Body[...]``.
    Le wrapper retourné possède exactement la même signature (ParamSpec) :
    l'appel ``GetUser(id=Body("id"), what=Body("what"))`` est donc vérifié
    statiquement de bout en bout — noms des kwargs, types ``Body[...]``,
    paramètres manquants ou superflus.

    Au runtime, chaque ``Body`` est ré-résolu avec la valeur du champ du body
    avant l'appel du getter : ``id.value`` (typé ``T``) et ``id.name`` (``str``).
    """

    signature = inspect.signature(fnc)

    # Garde-fou à l'import : tous les paramètres doivent être annotés Body[...].
    hints = typing.get_type_hints(fnc)
    for param in signature.parameters.values():
        hint = hints.get(param.name)
        if typing.get_origin(hint) is not Body and hint is not Body:
            raise TypeError(
                f"@internal_multi_getter : le paramètre {param.name!r} de "
                + f"{fnc.__name__} doit être annoté Body[...], pas {hint!r}"
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
                    raw = data[ref.name]
                except KeyError:
                    raise KeyError(
                        f"{fnc.__name__} : le champ {ref.name!r} est absent du body"
                    ) from None
                resolved[param_name] = _bind(ref, raw)
            return cast(Callable[..., R], fnc)(**resolved)

        return Field(default_factory=factory)

    return wrapper


# ---------------------------------------------------------------------------
# Utilisation
# ---------------------------------------------------------------------------

# --- getters multi-champs ---------------------------------------------------


@internal_getter
def GetUser(id: Body[int], what: Body[str]) -> User:
    """Calcule à l'exécution l'utilisateur visé par le champ `id`.

    Le user courant doit être admin et avoir au moins un event lié à l'utilisateur.
    """
    return User(id.value, what.value)


@internal_getter
def GetOwner(id: Body[int]) -> User:
    """Cas mono-champ : l'ancien `internal_getter` devient un cas particulier."""
    return User(id.value, "admin")


# --- modèle d'entrée --------------------------------------------------------


class PutBody(BaseModel):
    what: str
    id: int
    user: Internal[User] = GetUser(id=Body("id"), what=Body("what"))
    owner: Internal[User] = GetOwner(id=Body("id"))


class login(BaseScope):
    @override
    def authorize(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> ScopeResponse:
        return OK


class admin(BaseScope, parents=login()):
    @override
    def authorize(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> ScopeResponse:

        return OK


t = PutBody(what="hello", id=1)
print(PutBody.model_fields["user"].default_factory.__dict__)


class GetResponse(BaseModel):
    id: int
    name: int


class PutJson(BaseModel):
    id: int
    name: str


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
        """hello world
        this put route allow you to send the data as one block"""
        print(body)
        return PutJson(id=2, name="bob")


# client = app.test_client()
# client.put()
