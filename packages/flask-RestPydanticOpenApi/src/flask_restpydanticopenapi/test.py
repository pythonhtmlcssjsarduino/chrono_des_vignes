from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    Literal,
    Self,
    cast,
    get_args,
    get_origin,
    override,
)

from pydantic.annotated_handlers import GetJsonSchemaHandler
from pydantic.json_schema import SkipJsonSchema
from pydantic_core import CoreSchema, PydanticOmit

from flask_restpydanticopenapi.api import Api
from flask_restpydanticopenapi.authorize import OK, BaseScope, ScopeResponse
from flask_restpydanticopenapi.resource import Resource

"""extracted from pydantic.json_schema.SkipJsonSchema"""

type _Internal[T: Any, M: InternalBase[Any, Any], S: str] = SkipJsonSchema[
    Annotated[T, M, S, Field(default_factory=lambda: None)]
]

if TYPE_CHECKING:
    type Internal[T: Any, M: InternalBase[Any, Any], S: str] = _Internal[T, M, S]
else:

    @dataclass(slots=True)
    class Internal[T: Any, M: InternalBase, S: str]:
        def __class_getitem__(cls, item: tuple[T, M, S]) -> T:
            return _Internal[*item]  # type: ignore

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


class InternalBase[P, R](ABC):
    __instance__: ClassVar[Self | None] = None

    @abstractmethod
    def compute(cls, field: P, field_name: str) -> R:
        pass

    @classmethod
    def _get_instance(cls) -> Self:
        if not cls.__instance__:
            cls.__instance__ = cls()
        return cls.__instance__

    @classmethod
    def get(cls, model: BaseModel, caller_field_name: str) -> R:
        model_cls = type(model)
        instance = cls._get_instance()
        caller = model_cls.model_fields.get(caller_field_name)
        if not caller:
            raise ValueError(f"Field {caller_field_name} not found in model")
        assert caller.annotation
        print(get_origin(caller.annotation), get_args(caller.annotation))
        if not (
            get_origin(caller.annotation) is _Internal
            and get_args(caller.annotation)[1] is cls
        ):
            raise ValueError(
                f"Field {caller_field_name} is not annotated with {cls.__name__}"
            )
        field_name = cast(str, get_args(caller.annotation)[2])

        if field_name not in model_cls.model_fields:
            raise ValueError(f"Field {field_name} not found in model")

        return instance.compute(getattr(model, field_name), field_name)


class GetUser(InternalBase[int, User]):
    @override
    def compute(cls, field: int, field_name: str) -> User:
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
    user: Internal[User, GetUser, Literal["id"]]


t = PutBody(what="hello", id=1)
for name, field in PutBody.model_fields.items():
    if get_origin(field.annotation) is _Internal:
        get_args(field.annotation)[1].get(PutBody, name)


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
