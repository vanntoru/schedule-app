from __future__ import annotations

import os
import pytest
from flask import Flask

from schedule_app import create_app

# ---------------------------------------------------------------------------
# Prep dummy env vars so create_app() works without real GCP creds
# ---------------------------------------------------------------------------
os.environ.setdefault("GCP_PROJECT", "dummy-project")
os.environ.setdefault("GOOGLE_CLIENT_ID", "dummy-client-id")


@pytest.fixture()
def app() -> Flask:
    return create_app(testing=True)


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


def test_generate_simple(client) -> None:
    resp = client.post("/api/schedule/generate?date=2025-01-01")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert set(data.keys()) == {"date", "slots", "unplaced"}
    assert data["date"] == "2025-01-01"
    assert len(data["slots"]) == 144


def test_generate_accepts_z_datetime(client) -> None:
    resp = client.post("/api/schedule/generate?date=2025-01-01T00:00:00Z")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert data["date"] == "2025-01-01"


def test_generate_accepts_naive_datetime(client) -> None:
    resp = client.post("/api/schedule/generate?date=2025-01-01T00:00:00")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert data["date"] == "2025-01-01"


def test_generate_naive_datetime_midday(client) -> None:
    resp = client.post("/api/schedule/generate?date=2025-07-05T15:00:00")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert data["date"] == "2025-07-05"
