import os
from pathlib import Path
import sys

import pytest

pytest.importorskip("flask")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from schedule_app import create_app

GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"


def _make_app():
    os.environ.setdefault("FLASK_SECRET", "test-secret")
    os.environ.setdefault("GOOGLE_CLIENT_ID", "client-id")
    os.environ.setdefault("GOOGLE_REDIRECT_URI", "http://localhost:5173/oauth2callback")
    return create_app()


def test_login_redirect_and_session():
    app = _make_app()
    with app.test_client() as client:
        resp = client.get("/login")
        assert resp.status_code == 302
        assert "accounts.google.com" in resp.headers["Location"]
        with client.session_transaction() as sess:
            assert "code_verifier" in sess
            assert "oauth_state" in sess


def test_callback_exchanges_token_and_redirects(monkeypatch):
    app = _make_app()

    def fake_post(url, data=None, timeout=None):
        fake_post.called = True
        fake_post.url = url
        fake_post.data = data

        class Resp:
            status_code = 200

            @staticmethod
            def json():
                return {
                    "access_token": "a",
                    "refresh_token": "r",
                    "expires_in": 3600,
                }

        return Resp()

    monkeypatch.setattr("schedule_app.__init__.requests.post", fake_post)

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["oauth_state"] = "abc"
            sess["code_verifier"] = "ver"
        resp = client.get("/oauth2callback?state=abc&code=code")
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/"
        with client.session_transaction() as sess:
            creds = sess.get("credentials")
            assert creds
            assert creds["access_token"] == "a"
            assert creds["refresh_token"] == "r"
    assert fake_post.called
    assert fake_post.url == GOOGLE_TOKEN_ENDPOINT

