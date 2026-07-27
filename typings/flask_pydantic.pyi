from typing import Any, Callable
from flask import Flask, Response
from pydantic import BaseModel

class FlaskPydantic:
    def __init__(self, app: Flask | None = None) -> None: ...
    def init_app(self, app: Flask) -> None: ...

def validate(
    model: BaseModel | None = None,
    body: BaseModel | None = None,
    query: BaseModel | None = None,
    on_success_status: int = 200,
    exclude_none: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Response]]: ...
def validate_request(
    model: BaseModel,
    exclude_none: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
def validate_response(
    model: BaseModel,
    on_success_status: int = 200,
    exclude_none: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Response]]: ...
