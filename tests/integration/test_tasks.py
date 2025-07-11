from __future__ import annotations

import json
from typing import Any

import pytest
from flask import Flask

from schedule_app import create_app
from schedule_app.api.tasks import TASKS


@pytest.fixture()
def app() -> Flask:
    flask_app = create_app(testing=True)
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
    assert "id" in data
    assert data["earliest_start_utc"] == "2025-01-01T09:00:00Z"

    resp = client.get("/api/tasks")
    assert len(resp.get_json()) == 1


def test_microsecond_truncation(client) -> None:
    payload = {
        "title": "Task",
        "category": "general",
        "duration_min": 20,
        "duration_raw_min": 25,
        "priority": "A",
        "earliest_start_utc": "2025-01-01T09:00:00.123456Z",
    }
    resp = client.post("/api/tasks", json=payload)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["earliest_start_utc"] == "2025-01-01T09:00:00Z"


def test_validation_error(client) -> None:
    payload = {
        "title": "bad",
        "category": "g",
        "duration_min": 21,
        "duration_raw_min": 7,
        "priority": "A",
    }
    resp = client.post("/api/tasks", json=payload)
    assert resp.status_code == 422
    data = resp.get_json()
    _assert_problem_details(data)
    assert data["detail"] == "Duration must be a positive multiple of 5 minutes."


def test_invalid_priority(client) -> None:
    payload = {
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
        "title": "T",
        "category": "c",
        "duration_min": 10,
        "duration_raw_min": 10,
        "priority": "B",
    }
    resp = client.post("/api/tasks", json=payload)
    task_id = resp.get_json()["id"]

    upd = payload | {"title": "Updated"}
    resp = client.put(f"/api/tasks/{task_id}", json=upd)
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Updated"

    del_resp = client.delete(f"/api/tasks/{task_id}")
    assert del_resp.status_code == 204

    resp = client.get("/api/tasks")
    assert resp.get_json() == []

