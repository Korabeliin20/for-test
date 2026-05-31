from collections.abc import Callable
from enum import StrEnum
from typing import Any

from requests import Response

from yatl.utils import get_content_type

from .json_validator import coerce_to_actual_type, validate_json_body
from .text_validator import validate_text_body
from .xml_validator import validate_xml_body


class ContentFormat(StrEnum):
    """Unified enumeration for content formats.

    Combines both format names and their corresponding MIME types.
    """

    JSON = "json"
    XML = "xml"
    TEXT = "text"

    @property
    def mime_type(self) -> str:
        """Returns the MIME type for this format.

        Returns:
            The MIME type string (e.g., "application/json" for JSON).
        """
        mapping = {
            self.JSON: "application/json",
            self.XML: "application/xml",
            self.TEXT: "text/plain",
        }
        return mapping[self]

    @classmethod
    def from_mime_type(cls, mime_type: str) -> "ContentFormat":
        """Determines the format from a MIME type.

        Args:
            mime_type: The MIME type string (e.g., "application/json").

        Returns:
            The corresponding ContentFormat enum value.

        Raises:
            ValueError: If the MIME type is not supported.
        """
        normalized = get_content_type(mime_type)
        mapping = {
            "application/json": cls.JSON,
            "application/xml": cls.XML,
            "text/plain": cls.TEXT,
        }
        if normalized in mapping:
            return mapping[normalized]
        raise ValueError(f"Unsupported content type: {mime_type}")


class ResponseValidator:
    """Validates an HTTP response against a set of expectations.

    Expectations can include status code, headers, and body content (JSON, XML,
    or plain text). Validation failures raise `AssertionError` with descriptive
    messages.
    """

    _body_validators = {
        ContentFormat.JSON: validate_json_body,
        ContentFormat.XML: validate_xml_body,
        ContentFormat.TEXT: validate_text_body,
    }

    def __init__(self, response: Response, expect_spec: dict[str, Any]):
        """Initializes the validator with a response and expectation spec.

        Args:
            response: The HTTP response to validate.
            expect_spec: A dictionary containing expectations (status, headers, body).
        """
        self.response = response
        self.expect_spec = expect_spec

    def _validate_status(self) -> None:
        """Validates that the response status code matches the expected one.

        Raises:
            AssertionError: If the status code does not match.
        """
        expected_status = self.expect_spec.get("status")
        expected_status = coerce_to_actual_type(
            expected_status, self.response.status_code
        )
        if expected_status is not None and self.response.status_code != expected_status:
            raise AssertionError(
                f"Expected status {expected_status}, got {self.response.status_code}"
            )

    def _validate_headers(self) -> None:
        """Validates that all expected headers are present and match.

        Raises:
            AssertionError: If a header is missing or its normalized value
                does not match the expected one.
        """
        expected_headers = self.expect_spec.get("headers")
        if expected_headers:
            for key, expected_value in expected_headers.items():
                actual = self.response.headers.get(key)
                if actual is None:
                    raise AssertionError(f"Header '{key}' is missing")
                if key.lower() == "content-type":
                    norm_expected = get_content_type(expected_value)
                    norm_actual = get_content_type(actual)
                else:
                    norm_expected = expected_value
                    norm_actual = actual

                norm_expected = coerce_to_actual_type(norm_expected, norm_actual)

                if norm_actual != norm_expected:
                    raise AssertionError(
                        f"Header '{key}' expected '{norm_expected}', got '{norm_actual}' (original: '{actual}')"
                    )

    def _get_body_validator(self, content_type: str) -> Callable | None:
        """Return appropriate body validator based on content-type.

        Args:
            content_type: The content-type string.

        Returns:
            A validator function or None if no match.
        """
        try:
            fmt = ContentFormat.from_mime_type(content_type)
            return self._body_validators.get(fmt)
        except ValueError:
            return None

    def _extract_format_and_spec(self, body_spec: Any) -> tuple[ContentFormat, Any]:
        """
        Extracts the format and spec from the body spec.

        Args:
            body_spec: The body spec to extract from.

        Returns:
            A tuple containing the format and the spec.

        Raises:
            AssertionError: If the body_spec is not a dict with one of
                {ContentFormat} keys (json, xml, or text).

        """
        if isinstance(body_spec, dict):
            for fmt in ContentFormat:
                if fmt in body_spec:
                    return fmt, body_spec[fmt]

        raise AssertionError(
            f"Body spec must be a dict with one of {list(ContentFormat)} keys, "
            f"got: {type(body_spec).__name__}"
        )

    def _validate_body(self, body_format: ContentFormat, body_spec: Any) -> None:
        """
        Validates the response body based on format.

        Raises:
            AssertionError: If the body validation fails.
        """
        validator = self._body_validators.get(body_format)
        if validator is None:
            raise AssertionError(f"No validator for format: {body_format}")
        validator(self.response, body_spec)

    def check_expectations(self) -> None:
        """Runs all validations defined in the expectation spec.

        Validates status, headers, and body (based on content-type). The body
        validation is dispatched to the appropriate validator (JSON, XML, or text).

        Raises:
            AssertionError: If any validation fails.
        """
        self._validate_status()
        self._validate_headers()

        body_spec = self.expect_spec.get("body")
        if body_spec is None:
            return

        body_format, body_spec = self._extract_format_and_spec(body_spec)
        self._validate_body(body_format, body_spec)
