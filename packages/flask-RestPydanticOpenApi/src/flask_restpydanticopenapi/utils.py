import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any

from pydantic.annotated_handlers import GetJsonSchemaHandler
from pydantic_core import CoreSchema, PydanticOmit


def generate_url(rule: str, version: int, api_prefix: str) -> str:
    return f"{api_prefix}/v{version}{rule}"


def get_path_params_from_rule(rule: str) -> dict[str, str]:
    """
    Extract path parameter names and their converter types from a Flask/Werkzeug rule string.

    Args:
        rule: The URL rule string (e.g., "/user/<int:user_id>/<string:name>").

    Returns:
        A dictionary mapping parameter names to their converter types.
        Example: {"user_id": "int", "name": "string"}.
    """
    # Regex to match <converter:param_name> or <param_name>
    pattern = r"<(?:([^:>]+):)?([^>]+)>"
    matches: list[tuple[str, str]] = re.findall(pattern, rule)

    params: dict[str, str] = {}
    for converter, param_name in matches:
        # Default converter is 'string' if not specified
        params[param_name] = converter or "default"

    return params


"""extracted from pydantic.json_schema.SkipJsonSchema"""

if TYPE_CHECKING:
    type Backend[AnyType] = Annotated[AnyType, ...]
else:

    @dataclass(slots=True)
    class Backend[AnyType]:
        """!!! abstract "Usage Documentation"
            [`SkipJsonSchema` Annotation](../concepts/json_schema.md#skipjsonschema-annotation)

        Add this as an annotation on a field to skip generating a JSON schema for that field.

        Example:
            ```python
            from pprint import pprint
            from typing import Union

            from pydantic import BaseModel
            from pydantic.json_schema import SkipJsonSchema

            class Model(BaseModel):
                a: Union[int, None] = None  # (1)!
                b: Union[int, SkipJsonSchema[None]] = None  # (2)!
                c: SkipJsonSchema[Union[int, None]] = None  # (3)!

            pprint(Model.model_json_schema())
            '''
            {
                'properties': {
                    'a': {
                        'anyOf': [
                            {'type': 'integer'},
                            {'type': 'null'}
                        ],
                        'default': None,
                        'title': 'A'
                    },
                    'b': {
                        'default': None,
                        'title': 'B',
                        'type': 'integer'
                    }
                },
                'title': 'Model',
                'type': 'object'
            }
            '''
            ```

            1. The integer and null types are both included in the schema for `a`.
            2. The integer type is the only type included in the schema for `b`.
            3. The entirety of the `c` field is omitted from the schema.
        """

        def __class_getitem__(cls, item: AnyType) -> AnyType:
            return Annotated[item, cls()]

        def __get_pydantic_json_schema__(
            self, core_schema: CoreSchema, handler: GetJsonSchemaHandler
        ) -> dict[str, Any]:
            raise PydanticOmit

        def __hash__(self) -> int:
            return hash(type(self))
