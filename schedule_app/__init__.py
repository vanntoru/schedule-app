"""Minimal Flask application factory.

This module avoids importing Flask at module import time when the package is
used purely for utilities (e.g. during unit tests).  The heavy import occurs
only inside :func:`create_app`.
"""

from __future__ import annotations

import os
from werkzeug.exceptions import HTTPException

from schedule_app.services.google_client import GoogleClient
from schedule_app.exceptions import APIError

try:  # Flask may be absent in some test environments
    from flask import Flask  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Flask = None  # type: ignore

try:
    from google_auth_oauthlib.flow import Flow  # type: ignore
    from flask import session, redirect, url_for, abort  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Flow = None  # type: ignore


def _get_setting(name: str) -> str | None:
    """Return OAuth setting from Flask config or environment."""

    from flask import current_app

    return current_app.config.get(name) or os.getenv(name)


def _build_flow(*, redirect_uri: str) -> Flow:
    """Return an OAuth2 Flow object."""
    if Flow is None:
        raise RuntimeError("google-auth-oauthlib is required")

    client_id = _get_setting("GOOGLE_CLIENT_ID")
    client_secret = _get_setting("GOOGLE_CLIENT_SECRET")

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret or "",
            "redirect_uris": [redirect_uri],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    # OAuth2 認証スコープをURI形式で指定（短縮表記を使用しない）
    scopes = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/spreadsheets",
    ]

    return Flow.from_client_config(
        client_config,
        scopes=scopes,
        redirect_uri=redirect_uri,
    )

def create_app(*, testing: bool = False) -> Flask:  # type: ignore[name-defined]
    """Return a minimal Flask application.

    Parameters
    ----------
    testing:
        When ``True``, enable Flask testing mode and disable CSRF protection.
    """
    if Flask is None:  # pragma: no cover - import guard for tests
        raise RuntimeError("Flask is required to create the application")

    from flask import jsonify, render_template, request

    app = Flask(__name__)
    app.secret_key = "dev-secret-key"

    # Lightweight Google API client stub
    app.extensions["gclient"] = GoogleClient(credentials=None)

    @app.after_request
    def _allow_service_worker(response):
        if request.path == "/static/sw.js":
            response.headers["Service-Worker-Allowed"] = "/"
        return response

    if testing:
        app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    from schedule_app.api import calendar_bp, tasks_bp, schedule_bp
    from schedule_app.api.blocks import init_blocks_api

    if calendar_bp is not None:
        app.register_blueprint(calendar_bp)

    if tasks_bp is not None:
        app.register_blueprint(tasks_bp)

    if schedule_bp is not None:
        app.register_blueprint(schedule_bp)

    # blocks API
    init_blocks_api(app)

    # ヘルスチェック用エンドポイント
    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    # 暫定トップページ
    @app.get("/")
    def index():
        """Render the main page with optional local Tailwind."""
        local_tw = os.getenv("LOCAL_TW") == "1"
        return render_template("index.html", local_tw=local_tw)

    @app.get("/login")
    def login():
        """Begin the OAuth2 PKCE flow and redirect the user."""

        redirect_uri = _get_setting("GOOGLE_REDIRECT_URI")
        flow = _build_flow(redirect_uri=redirect_uri)
        auth_url, state = flow.authorization_url(
            include_granted_scopes="true",
            code_challenge_method="S256",
        )
        session["pkce_state"] = state
        session["pkce_verifier"] = flow.code_verifier
        return redirect(auth_url)

    @app.get("/callback")
    def callback():
        """Exchange the code for tokens and store credentials."""

        if request.args.get("state") != session.get("pkce_state"):
            abort(400)

        code = request.args.get("code")
        if not code:
            abort(400)

        redirect_uri = _get_setting("GOOGLE_REDIRECT_URI")
        flow = _build_flow(redirect_uri=redirect_uri)
        flow.code_verifier = session.get("pkce_verifier")
        flow.fetch_token(code=code)

        creds = flow.credentials
        session["credentials"] = {
            "access_token": creds.token,
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        }
        return redirect(url_for("index"))

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        status = exc.code or 500
        code = "invalid-field" if status == 422 else exc.name.lower().replace(" ", "-")
        title = "Validation failed" if status == 422 else exc.name
        payload = {
            "type": f"https://schedule.app/errors/{code}",
            "title": title,
            "status": status,
            "detail": exc.description,
            "instance": request.path,
        }
        response = jsonify(payload)
        response.status_code = status
        response.mimetype = "application/problem+json"
        return response

    @app.errorhandler(APIError)
    def handle_api_error(exc: APIError):
        payload = {
            "type": "https://schedule.app/errors/bad-gateway",
            "title": "Bad Gateway",
            "status": 502,
            "detail": getattr(exc, "description", str(exc)),
            "instance": request.path,
        }
        response = jsonify(payload)
        response.status_code = 502
        response.mimetype = "application/problem+json"
        return response

    return app


# `flask --app schedule_app run` で自動検出されるエントリ
if Flask is not None:  # pragma: no cover - optional in test env
    app = create_app()
else:  # keep a stub for type checkers
    app = None  # type: ignore
