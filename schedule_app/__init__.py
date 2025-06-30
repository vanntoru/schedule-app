"""Minimal Flask application factory.

This module avoids importing Flask at module import time when the package is
used purely for utilities (e.g. during unit tests).  The heavy import occurs
only inside :func:`create_app`.
"""

from __future__ import annotations

import json
import os

try:
    from google_auth_oauthlib.flow import Flow  # type: ignore
    import google.oauth2.credentials as gcreds  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Flow = None  # type: ignore
    gcreds = None  # type: ignore

try:  # Flask may be absent in some test environments
    from flask import Flask  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Flask = None  # type: ignore


def login() -> "Response":
    from flask import current_app, redirect, request, session

    if Flow is None:
        raise RuntimeError("google-auth-oauthlib is required")

    client_id = os.getenv("GOOGLE_CLIENT_ID") or current_app.config.get("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or current_app.config.get("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI") or current_app.config.get("GOOGLE_REDIRECT_URI")

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
        include_granted_scopes="true", code_challenge_method="S256"
    )
    session["pkce_state"] = state
    return redirect(authorization_url)


def oauth2_cb() -> "Response":
    from flask import current_app, redirect, request, session, url_for

    if Flow is None:
        raise RuntimeError("google-auth-oauthlib is required")

    state = request.args.get("state")
    if not state or state != session.get("pkce_state"):
        return "Invalid state parameter", 400

    client_id = os.getenv("GOOGLE_CLIENT_ID") or current_app.config.get("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or current_app.config.get("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI") or current_app.config.get("GOOGLE_REDIRECT_URI")

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

    flow.fetch_token(code=request.args.get("code"))
    creds_dict = json.loads(flow.credentials.to_json())
    session["google_creds"] = creds_dict
    return redirect(url_for("index"))

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

    app.add_url_rule("/login", "login", login)
    app.add_url_rule("/callback", "oauth2_cb", oauth2_cb)

    return app


# `flask --app schedule_app run` で自動検出されるエントリ
if Flask is not None:  # pragma: no cover - optional in test env
    app = create_app()
else:  # keep a stub for type checkers
    app = None  # type: ignore
