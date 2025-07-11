from __future__ import annotations

import json
from typing import Any

import pytest
from flask import Flask

from schedule_app import create_app
from schedule_app.api.tasks import TASKS
from schedule_app.models import Task
from schedule_app.services.sheets_tasks import InvalidSheetRowError
from unittest.mock import patch


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


def test_invalid_earliest_start_format(client) -> None:
    payload = {
        "title": "Task",
        "category": "general",
        "duration_min": 20,
        "duration_raw_min": 20,
        "priority": "A",
        "earliest_start_utc": "not-a-date",
    }
    resp = client.post("/api/tasks", json=payload)
    assert resp.status_code == 422
    data = resp.get_json()
    _assert_problem_details(data)
    assert data["detail"] == "Invalid datetime format."


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


def test_import_tasks_success(client) -> None:
    sample_tasks = [
        Task(
            id="t1",
            title="A",
            category="c",
            duration_min=10,
            duration_raw_min=10,
            priority="A",
        )
    ]

    with patch(
        "schedule_app.api.tasks.fetch_tasks_from_sheet",
        return_value=sample_tasks,
    ):
        resp = client.get("/api/tasks/import")

    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == "t1"


def test_import_tasks_validation_error(client) -> None:
    with patch(
        "schedule_app.api.tasks.fetch_tasks_from_sheet",
        side_effect=InvalidSheetRowError("bad"),
    ):
        resp = client.get("/api/tasks/import")

    assert resp.status_code == 422
    _assert_problem_details(resp.get_json())


def test_import_tasks_api_error(client) -> None:
    with patch(
        "schedule_app.api.tasks.fetch_tasks_from_sheet",
        side_effect=Exception("boom"),
    ):
        resp = client.get("/api/tasks/import")

    assert resp.status_code == 502
    _assert_problem_details(resp.get_json())


def _create_sample_task(client) -> str:
    payload = {
        "title": "Old",
        "category": "c",
        "duration_min": 10,
        "duration_raw_min": 10,
        "priority": "A",
    }
    resp = client.post("/api/tasks", json=payload)
    return resp.get_json()["id"]


def test_import_tasks_post_replace(client) -> None:
    old_id = _create_sample_task(client)

    new_tasks = [
        Task(
            id="n1",
            title="New",
            category="c",
            duration_min=20,
            duration_raw_min=20,
            priority="A",
        )
    ]

    with patch(
        "schedule_app.api.tasks.fetch_tasks_from_sheet",
        return_value=new_tasks,
    ):
        resp = client.post("/api/tasks/import")

    assert resp.status_code == 204

    resp = client.get("/api/tasks")
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["id"] == "n1"
    assert data[0]["id"] != old_id


def test_import_tasks_post_validation_error(client) -> None:
    old_id = _create_sample_task(client)

    with patch(
        "schedule_app.api.tasks.fetch_tasks_from_sheet",
        side_effect=InvalidSheetRowError("bad"),
    ):
        resp = client.post("/api/tasks/import")

    assert resp.status_code == 422
    _assert_problem_details(resp.get_json())

    resp = client.get("/api/tasks")
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["id"] == old_id


def test_import_tasks_post_api_error(client) -> None:
    old_id = _create_sample_task(client)

    with patch(
        "schedule_app.api.tasks.fetch_tasks_from_sheet",
        side_effect=Exception("boom"),
    ):
        resp = client.post("/api/tasks/import")

    assert resp.status_code == 502
    _assert_problem_details(resp.get_json())

    resp = client.get("/api/tasks")
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["id"] == old_id

