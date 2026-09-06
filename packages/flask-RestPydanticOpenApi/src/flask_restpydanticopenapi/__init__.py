"""
# Chrono Des Vignes
# a timing system for sports events
#
# Copyright © 2024-2026 Romain Maurer
# This file is part of Chrono Des Vignes
#
# Chrono Des Vignes is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version.
#
# Chrono Des Vignes is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more fcdetails.
# You should have received a copy of the GNU General Public License along with Chrono des vignes.
# If not, see <https://www.gnu.org/licenses/>.
#
# You may contact me at chrono-des-vignes@ikmail.com
# or from my github https://github.com/pythonhtmlcssjsarduino/chrono_des_vignes
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any, Literal, override

from flask import abort, g
from pydantic import Field
from pydantic.json_schema import SkipJsonSchema

from flask_restpydanticopenapi.api import Api, ApiVersion
from flask_restpydanticopenapi.authorize import OK, BaseScope, ScopeResponse
from flask_restpydanticopenapi.openapi_meta import add_doc_to_meta, get_meta_obj
from flask_restpydanticopenapi.resource import Resource
from flask_restpydanticopenapi.utils import Backend

__all__ = ["Api", "ApiVersion", "Resource"]


def main():
    from flask import Flask
    from flask_swagger_ui import get_swaggerui_blueprint
    from pydantic import BaseModel

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

    def testDb(id_field: str) -> SkipJsonSchema[str]:
        def factory(data: dict[str, Any]) -> Any:
            if data.get(id_field) == 0:
                abort(404, "not found")

            return g.get("hello") or data.get(id_field, -1)

        return Field(default_factory=factory)

    @dataclass()
    class User:
        id: int
        name: str

    class GetResponse(BaseModel):
        id: int
        name: int

    class PutJson(BaseModel):
        id: int
        name: str

    class PutBody(BaseModel):
        what: str
        id: int
        what_object: SkipJsonSchema[str] = testDb(id_field="id")

    print(PutBody.model_fields["user"].annotation)

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

    @v1.register("/hello")
    class hello(Resource):
        "hey"

        def delete(self) -> PutJson:
            return PutJson(id=2, name="bob")

    (api.get_openapi_spec())
    print(app.test_client().get("/api/v1/test/76").text)
    app.run(debug=True)


if __name__ == "__main__":
    main()
