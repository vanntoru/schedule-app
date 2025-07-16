from __future__ import annotations

from werkzeug.exceptions import HTTPException


class InvalidBlockRow(HTTPException):
    """Raised when a block row contains invalid data."""

    code = 422
    description = "Block row validation failed"


__all__ = ["InvalidBlockRow"]
