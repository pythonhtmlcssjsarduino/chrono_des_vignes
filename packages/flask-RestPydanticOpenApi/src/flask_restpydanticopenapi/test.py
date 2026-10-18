from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import wraps
from types import UnionType
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Callable,
    ClassVar,
    Literal,
    Self,
    cast,
    get_args,
    get_origin,
    override,
)

from pydantic.annotated_handlers import GetJsonSchemaHandler
from pydantic.fields import FieldInfo
from pydantic.json_schema import SkipJsonSchema
from pydantic_core import CoreSchema, PydanticOmit

from flask_restpydanticopenapi.api import Api
from flask_restpydanticopenapi.authorize import OK, BaseScope, ScopeResponse
from flask_restpydanticopenapi.resource import Resource
from typing_extensions import Union

from chrono_des_vignes import Base

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


def internal_getter[T, R](
    scoops: list[type[BaseScope]] | type[BaseScope] | None = None,
):
    """
    Parameters
    ----------
    scoops : list[type[BaseScope]] | type[BaseScope] | None
        scoops needed to acces this resource
    """

    def decorator(fnc: Callable[[T, str], R]) -> Callable[[str], Any]:
        @wraps(fnc)
        def wrapper(field_name: str):
            print(field_name)

            def factory(data: dict[str, Any]):
                print(data)
                field = data[field_name]
                print(field, field_name)
                res = fnc(field, field_name)
                return res

            return Field(default_factory=factory)

        return wrapper

    return decorator


@internal_getter()
def GetUser(field: int, field_name: str):
    """
    compute at runtime the user accessed with the id present in the field

    the current user need to be an admin and have at least one event linked with the user
    """
    return User(field, field_name)


class login(BaseScope):
    @override
    def authorize(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> ScopeResponse:
        return OK


class admin(BaseScope, parents=login()):
    @override
    def authorize(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> ScopeResponse:

        return OK


class PutBody(BaseModel):
    what: str
    id: int
    user: Internal[User] = GetUser("id")


t = PutBody(what="hello", id=1)
for name, field in PutBody.model_fields.items():
    pass


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


client = app.test_client()
client.put()
