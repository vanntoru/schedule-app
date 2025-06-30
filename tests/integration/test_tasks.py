from __future__ import annotations

import json
from typing import Any

import pytest
from flask import Flask

from schedule_app import create_app
from schedule_app.api.tasks import bp as tasks_bp, TASKS


@pytest.fixture()
def app() -> Flask:
    flask_app = create_app(testing=True)
    flask_app.register_blueprint(tasks_bp)
    return flask_app


@pytest.fixture()
def client(app: Flask):
    TASKS.clear()
    return app.test_client()


def _assert_problem_details(data: Any) -> None:
    assert isinstance(data, dict)
    for key in ("type", "title", "status"):
        assert key in data


def test_list_empty(client) -> None:
    resp = client.get("/api/tasks")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_create_and_get(client) -> None:
    payload = {
        "id": "1",
        "title": "Task",
        "category": "general",
        "duration_min": 20,
        "duration_raw_min": 25,
        "priority": "A",
        "earliest_start_utc": "2025-01-01T09:00:00Z",
    }
    resp = client.post("/api/tasks", json=payload)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["id"] == "1"
    assert data["earliest_start_utc"] == "2025-01-01T09:00:00Z"

    resp = client.get("/api/tasks")
    assert len(resp.get_json()) == 1


def test_validation_error(client) -> None:
    payload = {
        "id": "x",
        "title": "bad",
        "category": "g",
        "duration_min": 21,
        "duration_raw_min": 7,
        "priority": "A",
    }
    resp = client.post("/api/tasks", json=payload)
    assert resp.status_code == 422
    _assert_problem_details(resp.get_json())


def test_invalid_priority(client) -> None:
    payload = {
        "id": "p",
        "title": "badprio",
        "category": "g",
        "duration_min": 10,
        "duration_raw_min": 10,
        "priority": "C",
    }
    resp = client.post("/api/tasks", json=payload)
    assert resp.status_code == 422
    _assert_problem_details(resp.get_json())


def test_update_not_found(client) -> None:
    resp = client.put("/api/tasks/404", json={"duration_min": 10, "duration_raw_min": 10})
    assert resp.status_code == 404
    _assert_problem_details(json.loads(resp.data))


def test_update_and_delete(client) -> None:
    payload = {
        "id": "2",
        "title": "T",
        "category": "c",
        "duration_min": 10,
        "duration_raw_min": 10,
        "priority": "B",
    }
    client.post("/api/tasks", json=payload)

    upd = payload | {"title": "Updated"}
    resp = client.put("/api/tasks/2", json=upd)
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Updated"

    del_resp = client.delete("/api/tasks/2")
    assert del_resp.status_code == 204

    resp = client.get("/api/tasks")
    assert resp.get_json() == []

