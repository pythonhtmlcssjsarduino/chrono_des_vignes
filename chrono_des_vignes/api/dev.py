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

import json

from pydantic import BaseModel, Field
from pydantic.json_schema import models_json_schema


class BaseConfig(BaseModel):
    """
    Base configuration for the application.
    """

    debug: bool = False
    host: str = ""


class ServerConfig(BaseConfig):
    """
    Configuration for the server environment.
    """

    test: bool = False
    version: int
    server_name: str = "localhost"


class DevConfig(BaseConfig):
    """
    Configuration for the development environment.
    """

    test: bool = True
    version: int
    servers: list[ServerConfig] = Field(default_factory=list)


_, definitions = models_json_schema(
    [(model, "validation") for model in [DevConfig, BaseConfig, ServerConfig]],
    ref_template="#/components/schemas/{model}",
)
print(
    json.dumps(
        definitions,
        indent=4,
    ),
    _,
)  # Print the JSON representation of the DevConfig model
