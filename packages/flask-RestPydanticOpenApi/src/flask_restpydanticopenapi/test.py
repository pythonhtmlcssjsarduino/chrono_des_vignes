from __future__ import annotations

from dataclasses import dataclass
from typing import (
    Any,
)

from flask import Flask
from flask_swagger_ui import get_swaggerui_blueprint
from pydantic import BaseModel
from werkzeug.exceptions import NotFound

from flask_restpydanticopenapi.api import Api
from flask_restpydanticopenapi.authorize import (
    OK,
    ResultAcces,
    ScopeResponse,
    scope_it,
)
from flask_restpydanticopenapi.internal_getter import Body, internal_getter, raises
from flask_restpydanticopenapi.resource import Resource

api = Api()

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

v1 = api.version(1)


@dataclass()
class User:
    id: int
    name: str


@scope_it()
class login:
    """
    the user need to be authenticated to acces this protected route
    """

    def authorize(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> ScopeResponse:
        return OK


@scope_it(depends_on=login)
class admin:
    """the user need to be authenticated and an admin to access this route"""

    def authorize(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> ScopeResponse:
        return OK

    def authorize_result(self, result: object):

        match result:
            case User() as u:
                return ResultAcces.read_write if u.id == 3 else ResultAcces.denied
            case _:
                return ResultAcces.unknown


@scope_it()
class read_only:
    def authorize_result(self, result: object):
        return ResultAcces.read_only


@internal_getter(admin)
@raises(NotFound)
def GetUser(id: Body[int], what: Body[str]) -> User:
    """Calcule à l'exécution l'utilisateur visé par le champ `id`.

    Le user courant doit être admin et avoir au moins un event lié à l'utilisateur.
    """
    return User(id.value, what.value)


@internal_getter([login])
def GetOwner(id: Body[int]) -> User:
    """Cas mono-champ : l'ancien `internal_getter` devient un cas particulier."""
    return User(id.value, "admin")


class PutBody(BaseModel):
    what: str
    id: int
    user: User = GetUser(id=Body("id"), what=Body("what"))
    owner: User = GetOwner(id=Body("id"))


class GetResponse(BaseModel):
    id: int
    name: int


class PutJson(BaseModel):
    id: int
    name: int


@v1.register("/test/<int:name>")
class test(Resource):
    """hello world
    its me"""

    def get(self, name: int, id: int = 3) -> GetResponse:
        """this is my func docstring

        that is a description
        ---
        this will not show on the swager"""
        return GetResponse(id=id, name=name)

    def put(self, name: int, body: PutBody) -> PutJson:
        """hello world
        this put route allow you to send the data as one block"""
        print(body)
        return PutJson(id=2, name=name)


app = Flask(__name__)
app.debug = True
app.config["OPENAPI_MODE"] = "live"
api.init_app(app)
app.register_blueprint(swaggerui_blueprint)


# client = app.test_client()
# client.put()
app.run(host="localhost")
