"""Minimal Flask application factory.

This module avoids importing Flask at module import time when the package is
used purely for utilities (e.g. during unit tests).  The heavy import occurs
only inside :func:`create_app`.
"""

from __future__ import annotations

import os

try:  # Flask may be absent in some test environments
    from flask import (
        Flask,
        session,
        redirect,
        url_for,
        request,
        abort,
    )  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Flask = None  # type: ignore

from google_auth_oauthlib.flow import Flow
from google.oauth2 import credentials as gcreds

from schedule_app.services.google_client import SCOPES


def _build_flow(*, redirect_uri: str) -> Flow:
    """Create an OAuth2 flow using environment configuration."""

    client_config = {
        "web": {
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )

def create_app() -> Flask:  # type: ignore[name-defined]
    """Return a minimal Flask application."""
    if Flask is None:  # pragma: no cover - import guard for tests
        raise RuntimeError("Flask is required to create the application")

    from flask import jsonify, render_template
    from schedule_app.config import cfg

    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev")

    redirect_uri = cfg.OAUTH_REDIRECT_URI

    # ヘルスチェック用エンドポイント
    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    # 暫定トップページ
    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/login")
    def login():
        flow = _build_flow(redirect_uri=redirect_uri)
        authorization_url, state = flow.authorization_url(
            include_granted_scopes="true",
            code_challenge_method="S256",
        )
        session["pkce_state"] = state
        session["code_verifier"] = flow.code_verifier  # type: ignore[attr-defined]
        return redirect(authorization_url)

    @app.get("/callback")
    def callback():
        if request.args.get("state") != session.pop("pkce_state", None):
            abort(400)
        flow = _build_flow(redirect_uri=redirect_uri)
        flow.fetch_token(
            code=request.args["code"],
            code_verifier=session.pop("code_verifier"),
        )
        creds: gcreds.Credentials = flow.credentials  # type: ignore[assignment]
        session["google_creds"] = creds.to_json()
        return redirect(url_for("index"))

    return app


# `flask --app schedule_app run` で自動検出されるエントリ
if Flask is not None:  # pragma: no cover - optional in test env
    app = create_app()
else:  # keep a stub for type checkers
    app = None  # type: ignore
