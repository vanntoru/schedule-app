"""Minimal Flask application factory with OAuth callback stub."""
from __future__ import annotations

try:  # Flask may be absent in some test environments
    from flask import Flask  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Flask = None  # type: ignore

from flask import abort, jsonify, make_response, render_template, request


def _exchange_code_for_token(code: str):
    """Placeholder for the OAuth token exchange."""
    raise NotImplementedError


def create_app() -> Flask:  # type: ignore[name-defined]
    """Return a minimal Flask application."""
    if Flask is None:  # pragma: no cover - import guard for tests
        raise RuntimeError("Flask is required to create the application")

    app = Flask(__name__)

    # ヘルスチェック用エンドポイント
    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    # 暫定トップページ
    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/oauth2callback")
    def oauth2callback():
        resp = _exchange_code_for_token(request.args.get("code", ""))
        if getattr(resp, "status_code", None) != 200:
            problem = {
                "type": "about:blank",
                "title": "token exchange failed",
                "status": 422,
            }
            abort(make_response(jsonify(problem), 422))
        return jsonify(status="ok")

    return app


# `flask --app schedule_app run` で自動検出されるエントリ
if Flask is not None:  # pragma: no cover - optional in test env
    app = create_app()
else:  # keep a stub for type checkers
    app = None  # type: ignore
