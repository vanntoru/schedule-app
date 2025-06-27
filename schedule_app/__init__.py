"""Minimal Flask application factory.

This module avoids importing Flask at module import time when the package is
used purely for utilities (e.g. during unit tests).  The heavy import occurs
only inside :func:`create_app`.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import urllib.parse
from datetime import datetime, timedelta
from typing import Any

try:  # Flask may be absent in some test environments
    from flask import Flask  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Flask = None  # type: ignore

def create_app() -> Flask:  # type: ignore[name-defined]
    """Return a minimal Flask application."""
    if Flask is None:  # pragma: no cover - import guard for tests
        raise RuntimeError("Flask is required to create the application")

    from flask import (
        abort,
        jsonify,
        redirect,
        render_template,
        request,
        session,
        url_for,
    )

    import requests

    from .services.google_client import SCOPES

    app = Flask(__name__)

    # Use a secret key from the environment for session management.  Tests
    # may provide a fallback value.
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET", "dev-secret")

    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
    AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"

    # ヘルスチェック用エンドポイント
    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    # 暫定トップページ
    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/login")
    def login() -> Any:
        """Start OAuth2 login with Google using PKCE."""
        state = secrets.token_urlsafe(16)
        verifier = secrets.token_urlsafe(64)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )

        session["oauth_state"] = state
        session["code_verifier"] = verifier

        params = dict(
            response_type="code",
            client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
            redirect_uri=os.environ.get("GOOGLE_REDIRECT_URI", ""),
            scope=" ".join(SCOPES),
            state=state,
            code_challenge=challenge,
            code_challenge_method="S256",
            access_type="offline",
            prompt="consent",
        )
        return redirect(f"{AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}")

    @app.get("/oauth2callback")
    def oauth2callback() -> Any:
        """Exchange authorization code for tokens."""
        if request.args.get("state") != session.get("oauth_state"):
            abort(400, description="state mismatch")

        data = dict(
            grant_type="authorization_code",
            code=request.args["code"],
            client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
            redirect_uri=os.environ.get("GOOGLE_REDIRECT_URI", ""),
            code_verifier=session.get("code_verifier"),
        )

        resp = requests.post(TOKEN_ENDPOINT, data=data, timeout=10)
        if resp.status_code != 200:
            abort(502, description="token exchange failed")

        creds = resp.json()
        session["credentials"] = {
            "access_token": creds["access_token"],
            "refresh_token": creds.get("refresh_token"),
            "expires_at": (
                datetime.utcnow() + timedelta(seconds=creds["expires_in"])
            ).isoformat(),
        }
        return redirect(url_for("index"))

    return app


# `flask --app schedule_app run` で自動検出されるエントリ
if Flask is not None:  # pragma: no cover - optional in test env
    app = create_app()
else:  # keep a stub for type checkers
    app = None  # type: ignore
