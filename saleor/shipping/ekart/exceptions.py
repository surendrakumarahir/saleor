"""Custom exceptions for Ekart Logistics integration."""

from typing import Any


class EkartError(Exception):
    """Base exception for Ekart integration errors."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "ekart_error",
        status_code: int | None = None,
        details: Any = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class EkartConfigError(EkartError):
    """Raised when required Ekart configuration or credentials are missing."""

    def __init__(self, message: str):
        super().__init__(message, code="ekart_not_configured")


class EkartAPIError(EkartError):
    """Raised when Ekart API returns an error or unexpected response."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "ekart_api_error",
        status_code: int | None = None,
        details: Any = None,
    ):
        super().__init__(
            message,
            code=code,
            status_code=status_code,
            details=details,
        )
