from __future__ import annotations

from werkzeug.exceptions import BadGateway


class APIError(BadGateway):
    """Generic upstream API failure."""


__all__ = ["APIError"]
