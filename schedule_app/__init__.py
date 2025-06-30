"""Minimal Flask application factory.

This module avoids importing Flask at module import time when the package is
used purely for utilities (e.g. during unit tests).  The heavy import occurs
only inside :func:`create_app`.
"""

from __future__ import annotations

try:
    from google_auth_oauthlib.flow import Flow
    import google.oauth2.credentials as gcreds
except ModuleNotFoundError:  # pragma: no cover - offline test env
    class Flow:  # minimal fallback used only when dependency is missing
        state = "stub"

        @classmethod
        def from_client_config(cls, *_args, **_kwargs):
            return cls()

        def authorization_url(
            self,
            include_granted_scopes: str = "true",
            code_challenge_method: str = "S256",
        ):
            url = (
                "https://accounts.google.com/o/oauth2/auth?"
                "code_challenge=dummy&code_challenge_method=S256&"
                "client_id=dummy&state=stub"
            )
            return url, "stub"

        def fetch_token(self, code: str | None = None):
            return None

        @property
        def credentials(self):
            class _Creds:
                def to_json(self):
                    return "{}"

            return _Creds()

    class gcreds:  # type: ignore
        class Credentials:  # pragma: no cover - stub
            pass

try:  # Flask may be absent in some test environments
    from flask import Flask  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Flask = None  # type: ignore

def create_app() -> Flask:  # type: ignore[name-defined]
    """Return a minimal Flask application."""
    if Flask is None:  # pragma: no cover - import guard for tests
        raise RuntimeError("Flask is required to create the application")

    from flask import jsonify, render_template

    app = Flask(__name__)

    # ヘルスチェック用エンドポイント
    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    # 暫定トップページ
    @app.get("/")
    def index():
        return render_template("index.html")

    # === OAuth2 PKCE ルートを追加する ===
    @app.get("/login")
    def login():
        """Start OAuth2 authorization with PKCE."""
        from flask import session, redirect
        import os

        client_id = app.config.get("GOOGLE_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID")
        client_secret = app.config.get("GOOGLE_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET")
        redirect_uri = app.config.get("GOOGLE_REDIRECT_URI") or os.getenv("GOOGLE_REDIRECT_URI")

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uris": [redirect_uri],
                }
            },
            scopes=[
                "openid",
                "profile",
                "email",
                "https://www.googleapis.com/auth/calendar.readonly",
                "https://www.googleapis.com/auth/spreadsheets",
            ],
            redirect_uri=redirect_uri,
        )

        authorization_url, state = flow.authorization_url(
            include_granted_scopes="true",
            code_challenge_method="S256",
        )
        session["pkce_state"] = state
        if hasattr(flow, "code_verifier"):
            session["pkce_verifier"] = flow.code_verifier
        return redirect(authorization_url)

    @app.get("/callback")
    def oauth2_cb():
        """OAuth2 callback endpoint."""
        from flask import session, request, redirect, url_for
        import os, json

        state = request.args.get("state")
        if state != session.get("pkce_state"):
            return redirect(url_for("index"))

        client_id = app.config.get("GOOGLE_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID")
        client_secret = app.config.get("GOOGLE_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET")
        redirect_uri = app.config.get("GOOGLE_REDIRECT_URI") or os.getenv("GOOGLE_REDIRECT_URI")

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uris": [redirect_uri],
                }
            },
            scopes=[
                "openid",
                "profile",
                "email",
                "https://www.googleapis.com/auth/calendar.readonly",
                "https://www.googleapis.com/auth/spreadsheets",
            ],
            redirect_uri=redirect_uri,
            state=state,
        )
        if "pkce_verifier" in session:
            setattr(flow, "code_verifier", session["pkce_verifier"])

        code = request.args.get("code")
        if code:
            flow.fetch_token(code=code)
            creds_data = json.loads(flow.credentials.to_json())
            session["google_creds"] = creds_data

        return redirect(url_for("index"))

    return app


# `flask --app schedule_app run` で自動検出されるエントリ
if Flask is not None:  # pragma: no cover - optional in test env
    app = create_app()
else:  # keep a stub for type checkers
    app = None  # type: ignore
