import re


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
