"""Integration tests for OAuth2 PKCE login / callback flow."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Generator
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse
from types import ModuleType, SimpleNamespace

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

    # --- provide a minimal "flask" substitute ----------------------------
    dummy = ModuleType("flask")

    class DummyResponse:
        def __init__(self, status_code: int = 200, headers: dict | None = None):
            self.status_code = status_code
            self.headers = headers or {}

    dummy.session = {}

    def redirect(url: str) -> DummyResponse:
        return DummyResponse(status_code=302, headers={"Location": url})

    dummy.redirect = redirect
    dummy.url_for = lambda endpoint: "/"
    dummy.request = SimpleNamespace(args={})
    dummy.abort = lambda code: (_ for _ in ()).throw(RuntimeError(f"abort {code}"))
    dummy.jsonify = lambda **kw: DummyResponse(headers={"Content-Type": "application/json"})
    dummy.render_template = lambda tpl: DummyResponse()

    class DummyFlask:
        def __init__(self, name: str) -> None:
            self.name = name
            self.routes: dict[str, callable] = {}
            self.config: dict = {}

        def get(self, path: str):
            def decorator(func):
                self.routes[path] = func
                return func
            return decorator

        def test_client(self):
            app = self

            class Client:
                def __init__(self) -> None:
                    self.session = dummy.session

                def session_transaction(self):
                    class Ctx:
                        def __enter__(self_inner):
                            return self.session

                        def __exit__(self_inner, exc_type, exc, tb):
                            pass

                    return Ctx()

                def get(self, url: str, follow_redirects: bool = False):
                    parsed = urlparse(url)
                    qs = {k: v[0] if isinstance(v, list) else v for k, v in parse_qs(parsed.query).items()}
                    dummy.request.args = qs
                    route = app.routes.get(parsed.path)
                    if route is None:
                        raise AssertionError(f"no route {parsed.path}")
                    return route()

            return Client()

    dummy.Flask = DummyFlask

    sys.modules["flask"] = dummy

    # --- stub google-auth packages so imports succeed ---------------------
    flow_mod = ModuleType("google_auth_oauthlib.flow")
    class _DummyFlow:  # pragma: no cover - minimal stub
        pass

    flow_mod.Flow = _DummyFlow
    pkg_ga = ModuleType("google_auth_oauthlib")
    pkg_ga.flow = flow_mod
    sys.modules["google_auth_oauthlib"] = pkg_ga
    sys.modules["google_auth_oauthlib.flow"] = flow_mod

    cred_mod = ModuleType("google.oauth2.credentials")
    pkg_google = ModuleType("google.oauth2")
    pkg_google.credentials = cred_mod
    root_google = ModuleType("google")
    root_google.oauth2 = pkg_google
    sys.modules["google"] = root_google
    sys.modules["google.oauth2"] = pkg_google
    sys.modules["google.oauth2.credentials"] = cred_mod

    import importlib
    import schedule_app
    schedule_app = importlib.reload(schedule_app)
    from schedule_app import create_app  # import after patch

    flask_app = create_app()
    flask_app.config.update(TESTING=True, SECRET_KEY="test-secret")
    dummy.current_app = flask_app
    yield flask_app


@pytest.fixture()
def client(app):  # type: ignore[override]
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
        "https://accounts.google.com/o/oauth2/auth?code_challenge=x&code_challenge_method=S256&client_id=dummy",
        "state1",
    )
    dummy_flow.code_verifier = "ver"
    mock_flow_cls.from_client_config.return_value = dummy_flow

    resp = client.get("/login", follow_redirects=False)

    assert resp.status_code == 302
    location = resp.headers["Location"]
    assert "accounts.google.com" in location

    qs = parse_qs(urlparse(location).query)
    # code_challenge + S256 方式が含まれること
    assert qs.get("code_challenge_method") == ["S256"]
    assert "code_challenge" in qs
    assert "client_id" in qs


@patch("schedule_app.Flow")  # patch inside module where used
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
