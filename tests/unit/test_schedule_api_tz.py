from __future__ import annotations

import importlib
from datetime import date
from flask import Flask

from schedule_app.api import schedule as schedule_api
from schedule_app.services import schedule as schedule_service
from schedule_app import config as config_module


def _make_app():
    app = Flask(__name__)
    app.register_blueprint(schedule_api.schedule_bp)
    return app.test_client()


def test_generate_schedule_default_timezone(monkeypatch):
    captured = {}

    def fake_generate_schedule(*, target_day: date, algo: str):
        captured["day"] = target_day
        return {"date": str(target_day), "slots": [], "unplaced": [], "algo": algo}

    monkeypatch.setattr(schedule_service, "generate_schedule", fake_generate_schedule)
    client = _make_app()
    resp = client.post("/api/schedule/generate?date=2025-01-01")
    assert resp.status_code == 200
    assert captured["day"] == date(2024, 12, 31)


def test_generate_schedule_custom_timezone(monkeypatch):
    monkeypatch.setenv("TIMEZONE", "UTC")
    importlib.reload(config_module)
    importlib.reload(schedule_api)
    importlib.reload(schedule_service)

    captured = {}

    def fake_generate_schedule(*, target_day: date, algo: str):
        captured["day"] = target_day
        return {"date": str(target_day), "slots": [], "unplaced": [], "algo": algo}

    monkeypatch.setattr(schedule_service, "generate_schedule", fake_generate_schedule)
    client = _make_app()
    resp = client.post("/api/schedule/generate?date=2025-01-01")
    assert resp.status_code == 200
    assert captured["day"] == date(2025, 1, 1)

    monkeypatch.delenv("TIMEZONE", raising=False)
    importlib.reload(config_module)
    importlib.reload(schedule_api)
    importlib.reload(schedule_service)
