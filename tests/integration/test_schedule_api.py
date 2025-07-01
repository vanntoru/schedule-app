from __future__ import annotations

import pytest
from flask import Flask

from schedule_app import create_app


@pytest.fixture()
def app() -> Flask:
    return create_app(testing=True)


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


def test_generate_simple(client) -> None:
    payload = {
        "tasks": [
            {
                "id": "t1",
                "title": "T1",
                "category": "gen",
                "duration_min": 10,
                "duration_raw_min": 10,
                "priority": "A",
            }
        ],
        "events": [],
        "blocks": [],
    }
    resp = client.post("/api/schedule/generate?date=2025-01-01", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert len(data.get("slots", [])) == 144
