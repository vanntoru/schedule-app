"""Google API client stub for future implementation.

This module defines a minimal :class:`GoogleClient` with placeholders for
accessing Google Calendar and Google Sheets. Actual API integration will be
added later.
"""

from __future__ import annotations

from typing import Any

# OAuth scopes required for the application
# openid, profile and email allow user authentication,
# Calendar and Sheets readonly scopes provide read access
# to the user's calendar and spreadsheet data.
SCOPES = [
    "openid",
    "profile",
    "email",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


class GoogleClient:
    """Lightweight wrapper around Google service clients."""

    def __init__(self, credentials: Any) -> None:
        """Initialize the client with OAuth2 *credentials*."""
        self.credentials = credentials

    def calendar_service(self) -> Any:
        """Return a Google Calendar service client (stub)."""
        raise NotImplementedError

    def sheets_service(self) -> Any:
        """Return a Google Sheets service client (stub)."""
        raise NotImplementedError
