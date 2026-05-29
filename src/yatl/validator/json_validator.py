import json
from typing import Any

from requests import Response

from yatl.utils import get_nested_value


def coerce_to_actual_type(expected: Any, actual: Any) -> Any:
    """Aware type coercion for expected and actual values.

    Args:
        expected: The expected value.
        actual: The actual value.

    Returns:
        The coerced value.
    """
    if type(expected) is type(actual):
        return expected
    if isinstance(actual, bool):
        if isinstance(expected, str):
            if expected.lower() in ("true", "false"):
                return expected.lower() == "true"
    if isinstance(actual, int) and not isinstance(actual, bool):
        try:
            return int(expected)
        except (ValueError, TypeError):
            pass
    if isinstance(actual, float):
        try:
            return float(expected)
        except (ValueError, TypeError):
            pass
    if isinstance(actual, (list, dict)):
        if isinstance(expected, str):
            import json

            try:
                return json.loads(expected)
            except json.JSONDecodeError:
                pass

    return expected


def validate_json_body(response: Response, expected_json: dict[str, Any]) -> None:
    """Validates that the JSON response matches the expected structure.

    Args:
        response: The HTTP response containing JSON data.
        expected_json: A dictionary of expected key-value pairs.
            Nested dictionaries are validated recursively.

    Raises:
        AssertionError: If the response is not valid JSON, or any key
            is missing, or any value differs.
    """
    try:
        data = response.json()
    except json.JSONDecodeError:
        raise AssertionError("Response is not valid JSON")
    _validate_json_response(data, expected_json)


def _validate_json_response(
    data: dict[str, Any], expected_json: dict[str, Any]
) -> None:
    """Recursively validates a JSON object against an expected dictionary.

    Supports dot-notation keys for validating deep nested fields.

    Args:
        data: The actual JSON dictionary (or sub-dictionary).
        expected_json: The expected dictionary for this level.

    Raises:
        AssertionError: If a key is missing or a value mismatches.
    """
    for key, expected_value in expected_json.items():
        if "." in key:
            try:
                actual = get_nested_value(data, key)
            except ValueError as e:
                raise AssertionError(f"Path '{key}' not found in response: {e}")
            coerced = coerce_to_actual_type(expected_value, actual)
            if actual != coerced:
                raise AssertionError(
                    f"For path '{key}' expected '{expected_value}', got '{actual}'"
                )
        else:
            # Plain key
            if key not in data:
                raise AssertionError(f"Key '{key}' is missing in response")
            actual = data[key]
            if isinstance(actual, dict) and isinstance(expected_value, dict):
                _validate_json_response(actual, expected_value)
            elif actual != coerce_to_actual_type(expected_value, data[key]):
                raise AssertionError(
                    f"For key '{key}' expected '{expected_value}', got '{actual}'"
                )
