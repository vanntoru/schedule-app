from __future__ import annotations

import json
from datetime import datetime

import pytest
from flask import Flask

from schedule_app import create_app
from schedule_app.api.tasks import TASKS
from schedule_app.api.blocks import BLOCKS


class DummyGClient:
    def list_events(self, *, date: datetime):
        return []


@pytest.fixture()
def app() -> Flask:
    flask_app = create_app(testing=True)
    return flask_app


@pytest.fixture()
def client(app: Flask):
    TASKS.clear()
    BLOCKS.clear()
    return app.test_client()


def test_generate_success(app: Flask, client) -> None:
    app.extensions["gclient"] = DummyGClient()
    resp = client.post("/api/schedule/generate?date=2025-01-01")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 144


def test_generate_missing_date(app: Flask, client) -> None:
    app.extensions["gclient"] = DummyGClient()
    resp = client.post("/api/schedule/generate")
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert data["status"] == 400


def test_generate_invalid_date(app: Flask, client) -> None:
    app.extensions["gclient"] = DummyGClient()
    resp = client.post("/api/schedule/generate?date=2025/01/01")
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert data["status"] == 400


def test_generate_invalid_algo(app: Flask, client) -> None:
    app.extensions["gclient"] = DummyGClient()
    resp = client.post("/api/schedule/generate?date=2025-01-01&algo=bad")
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert data["status"] == 400
