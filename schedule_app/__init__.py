"""Minimal Flask application factory.

This module avoids importing Flask at module import time when the package is
used purely for utilities (e.g. during unit tests).  The heavy import occurs
only inside :func:`create_app`.
"""

from __future__ import annotations

try:  # Flask may be absent in some test environments
    from flask import Flask  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Flask = None  # type: ignore

try:
    from google_auth_oauthlib.flow import Flow  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Flow = None  # type: ignore


def _build_flow(*, redirect_uri: str) -> Flow:  # pragma: no cover - placeholder
    """Return an OAuth2 Flow object."""
    if Flow is None:
        raise RuntimeError("google-auth-oauthlib is required")
    raise NotImplementedError

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

    return app


# `flask --app schedule_app run` で自動検出されるエントリ
if Flask is not None:  # pragma: no cover - optional in test env
    app = create_app()
else:  # keep a stub for type checkers
    app = None  # type: ignore
