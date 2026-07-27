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

from typing import final
from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict


class CDVConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")  # pyright: ignore[reportUnannotatedClassAttribute]

    DB_PASSWORD: str
    DB_USER: str
    DB_HOST: str
    DB_NAME: str

    SERVER_NAME: str
    SECRET_KEY: str

    REDIS_HOST: str
    REDIS_PORT: int

    SENTRY_DNS: str
    SENTRY_ENVIRONMENT: str
    SENTRY_ENABLED: bool

    @property
    def DB_URI(self):
        return f"mysql+pymysql://{self.DB_USER}:{quote(self.DB_PASSWORD)}@{self.DB_HOST}/{self.DB_NAME}"


cdv_config = CDVConfig()  # pyright: ignore[reportCallIssue]


@final
class FlaskConfig:
    # server
    SERVER_NAME = cdv_config.SERVER_NAME
    SECRET_KEY = cdv_config.SECRET_KEY

    # data base
    SQLALCHEMY_DATABASE_URI = cdv_config.DB_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 280,  # refresh connections every ~280s
        "pool_pre_ping": True,  # check connection before using it
    }

    # pydantic
    FLASK_PYDANTIC_VALIDATION_ERROR_RAISE = True

    # babel
    BABEL_TRANSLATION_DIRECTORIES = "./translations"

    # redis
    REDIS_URL = f"redis://{cdv_config.REDIS_HOST}:{cdv_config.REDIS_PORT}"
