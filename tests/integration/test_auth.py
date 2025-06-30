"""Integration tests for OAuth2 PKCE login / callback flow."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Generator
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def app() -> Generator:  # type: ignore[override]
    """Return a Flask application configured for testing."""
    # 環境変数が未設定だと Flow 生成時に失敗するためダミー値を入れる
    os.environ.setdefault("GOOGLE_CLIENT_ID", "dummy-client-id")
    os.environ.setdefault("GOOGLE_CLIENT_SECRET", "dummy-secret")
    os.environ.setdefault("GOOGLE_REDIRECT_URI", "http://localhost:5173/callback")

    from schedule_app import create_app  # 遅延 import

    flask_app = create_app()
    flask_app.config.update(TESTING=True, SECRET_KEY="test‑secret")
    yield flask_app


@pytest.fixture()
def client(app):  # type: ignore[override]
    """Flask test client."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------



def test_login_redirects_to_google(client):
    """GET /login should 302 to Google OAuth endpoint with PKCE parameters."""
    resp = client.get("/login", follow_redirects=False)

    assert resp.status_code == 302
    location = resp.headers["Location"]
    assert "accounts.google.com" in location

    qs = parse_qs(urlparse(location).query)
    # code_challenge + S256 方式が含まれること
    assert qs.get("code_challenge_method") == ["S256"]
    assert "code_challenge" in qs
    assert "client_id" in qs


@patch("schedule_app.__init__.Flow")  # patch inside module where used
def test_callback_exchanges_code_and_stores_creds(mock_flow_cls, client, app):
    """/callback exchanges code→token, saves creds, then redirects home."""
    # ダミー Credentials (to_json だけ使う)
    dummy_creds = MagicMock()
    dummy_creds.to_json.return_value = json.dumps({"access_token": "ya29.test‑token"})

    # Flow インスタンスのモック
    mock_flow = MagicMock()
    mock_flow.fetch_token.return_value = None
    mock_flow.credentials = dummy_creds
    mock_flow_cls.from_client_config.return_value = mock_flow

    # CSRF 用 state を事前に session へ
    with client.session_transaction() as sess:
        sess["pkce_state"] = "abc123"

    resp = client.get("/callback?state=abc123&code=fake‑auth‑code", follow_redirects=False)

    # 正常ならホームへ 302
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")

    # セッションに認証情報が保存される
    with client.session_transaction() as sess:
        assert "google_creds" in sess
        creds = json.loads(sess["google_creds"])
        assert creds["access_token"].startswith("ya29.")
