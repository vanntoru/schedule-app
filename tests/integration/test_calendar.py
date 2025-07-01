from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pytest
from freezegun import freeze_time
from flask import Flask

from schedule_app import create_app
from schedule_app.api.calendar import HttpError, RefreshError
from schedule_app.models import Event


class DummyGClient:
    """Simple Google client mock."""

    def __init__(self, *, raise_exc: Exception | None = None, events: list[Event] | None = None) -> None:
        self.raise_exc = raise_exc
        self.events = events or []

    def list_events(self, *, date: datetime) -> list[Event]:
        if self.raise_exc:
            raise self.raise_exc
        return self.events


@pytest.fixture()
def app() -> Flask:
    flask_app = create_app(testing=True)
    return flask_app


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


def _assert_problem_details(data: Any) -> None:
    assert isinstance(data, dict)
    for key in ("type", "title", "status"):
        assert key in data


def test_calendar_missing_date(app: Flask, client) -> None:
    app.extensions["gclient"] = DummyGClient()
    resp = client.get("/api/calendar")
    assert resp.status_code == 400
    data = json.loads(resp.data)
    _assert_problem_details(data)


def test_calendar_invalid_date(app: Flask, client) -> None:
    app.extensions["gclient"] = DummyGClient()
    resp = client.get("/api/calendar?date=2025/01/01")
    assert resp.status_code == 400
    data = json.loads(resp.data)
    _assert_problem_details(data)


@freeze_time("2025-01-01T00:00:00Z")
def test_calendar_success(app: Flask, client) -> None:
    event = Event(
        id="1",
        start_utc=datetime(2025, 1, 1, 1, 0, tzinfo=timezone.utc),
        end_utc=datetime(2025, 1, 1, 2, 0, tzinfo=timezone.utc),
        title="Demo",
    )
    app.extensions["gclient"] = DummyGClient(events=[event])
    resp = client.get("/api/calendar?date=2025-01-01")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["title"] == "Demo"


@freeze_time("2025-01-01T00:00:00Z")
def test_calendar_stub_events(app: Flask, client) -> None:
    events = [
        Event(
            id="stub1",
            start_utc=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc),
            end_utc=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            title="Dummy Event 1",
        ),
        Event(
            id="stub2",
            start_utc=datetime(2025, 1, 1, 11, 0, tzinfo=timezone.utc),
            end_utc=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            title="Dummy Event 2",
        ),
    ]
    app.extensions["gclient"] = DummyGClient(events=events)
    resp = client.get("/api/calendar?date=2025-01-01")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["title"] == "Dummy Event 1"
    assert data[0]["start_utc"] == "2025-01-01T09:00:00+00:00"


@freeze_time("2025-01-01T00:00:00Z")
def test_calendar_unauthorized(app: Flask, client) -> None:
    app.extensions["gclient"] = DummyGClient(raise_exc=RefreshError("unauthorized"))
    resp = client.get("/api/calendar?date=2025-01-01")
    assert resp.status_code == 401
    data = json.loads(resp.data)
    _assert_problem_details(data)


@freeze_time("2025-01-01T00:00:00Z")
def test_calendar_forbidden(app: Flask, client) -> None:
    class FakeResp:
        status = 403
        reason = "Forbidden"

    app.extensions["gclient"] = DummyGClient(raise_exc=HttpError(FakeResp(), b""))
    resp = client.get("/api/calendar?date=2025-01-01")
    assert resp.status_code == 403
    data = json.loads(resp.data)
    _assert_problem_details(data)
