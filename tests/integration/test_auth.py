"""Integration tests for OAuth2 PKCE login / callback flow (real Flask)."""

from __future__ import annotations

import os
from urllib.parse import parse_qs, urlparse
from unittest.mock import MagicMock, patch

from schedule_app.services.google_client import SCOPES

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
# ---------------------------------------------------------------------------
# Prep: dummy OAuth env vars so Flow.init succeeds even without real creds
# ---------------------------------------------------------------------------

os.environ.setdefault("GOOGLE_CLIENT_ID", "dummy-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "dummy-secret")
os.environ.setdefault("OAUTH_REDIRECT_URI", "http://localhost:5173/callback")

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def app():
    """Real Flask app from create_app(), in TESTING mode."""
    from schedule_app import create_app

    flask_app = create_app(testing=True)
    flask_app.config.update(SECRET_KEY="test-secret")
    return flask_app


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@patch("schedule_app.Flow")
def test_login_redirects_to_google(mock_flow_cls, client):
    """GET /login should 302 to Google OAuth endpoint with PKCE parameters."""
    dummy_flow = MagicMock()
    dummy_flow.authorization_url.return_value = (
        "https://accounts.google.com/o/oauth2/auth?"
        "code_challenge=xyz&code_challenge_method=S256&client_id=dummy",
        "state1",
    )
    dummy_flow.code_verifier = "verifierxyz"
    mock_flow_cls.from_client_config.return_value = dummy_flow

    resp = client.get("/login", follow_redirects=False)
    assert resp.status_code == 302

    # verify Flow.from_client_config called with expected scopes
    called_scopes = mock_flow_cls.from_client_config.call_args.kwargs.get("scopes")
    assert called_scopes == SCOPES
    assert "https://www.googleapis.com/auth/spreadsheets.readonly" in called_scopes
    assert "https://www.googleapis.com/auth/userinfo.profile" in called_scopes
    assert "https://www.googleapis.com/auth/userinfo.email" in called_scopes

    loc = resp.headers["Location"]
    assert "accounts.google.com" in loc

    qs = parse_qs(urlparse(loc).query)
    assert qs.get("code_challenge_method") == ["S256"]
    assert "code_challenge" in qs
    assert "client_id" in qs


@patch("schedule_app.Flow")
def test_callback_exchanges_code_and_stores_creds(mock_flow_cls, client):
    """GET /callback exchanges code→token, stores creds, and redirects home."""
    dummy_creds = MagicMock()
    dummy_creds.token = "ya29.test-token"
    dummy_creds.expiry = None

    dummy_flow = MagicMock()
    dummy_flow.fetch_token.return_value = None
    dummy_flow.credentials = dummy_creds
    mock_flow_cls.from_client_config.return_value = dummy_flow

    # preload CSRF state
    with client.session_transaction() as sess:
        sess["pkce_state"] = "abc123"

    resp = client.get("/callback?state=abc123&code=fake-auth-code", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")

    with client.session_transaction() as sess:
        assert sess.get("credentials") == {
            "access_token": "ya29.test-token",
            "expiry": None,
        }
