from __future__ import annotations


class AppError(Exception):
    """Base app error."""


class BadRequestError(AppError):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class UpstreamError(AppError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class UpstreamTimeoutError(AppError):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

