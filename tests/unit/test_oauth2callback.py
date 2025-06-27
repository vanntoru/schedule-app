from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path
import sys

import pytest

# Make package importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from schedule_app import create_app  # noqa: E402


def test_oauth2callback_returns_422(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    client = app.test_client()

    def fake_exchange(code: str) -> SimpleNamespace:
        return SimpleNamespace(status_code=500)

    monkeypatch.setattr(
        "schedule_app.__init__._exchange_code_for_token",
        fake_exchange,
    )

    resp = client.get("/oauth2callback?code=abc")
    assert resp.status_code == 422
    json_data = resp.get_json()
    assert json_data["title"] == "token exchange failed"
    assert json_data["status"] == 422
