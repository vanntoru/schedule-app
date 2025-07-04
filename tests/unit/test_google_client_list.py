from datetime import datetime, timezone

from schedule_app.models import Event
from schedule_app.services.google_client import GoogleClient


def test_list_events_range(monkeypatch):
    client = GoogleClient(credentials=None)

    captured = {}

    def fake_fetch(*, time_min: str, time_max: str):
        captured["time_min"] = time_min
        captured["time_max"] = time_max
        return []

    monkeypatch.setattr(client, "fetch_calendar_events", fake_fetch)

    client.list_events(date=datetime(2025, 1, 1))

    assert captured["time_min"] == "2024-12-31T15:00:00Z"
    assert captured["time_max"] == "2025-01-01T15:00:00Z"


def test_list_events_dataclass(monkeypatch):
    client = GoogleClient(credentials=None)

    sample = {
        "id": "1",
        "summary": "Demo",
        "start": {"dateTime": "2025-01-01T01:00:00Z"},
        "end": {"dateTime": "2025-01-01T02:00:00Z"},
    }

    def fake_fetch(*, time_min: str, time_max: str):
        return [sample]

    monkeypatch.setattr(client, "fetch_calendar_events", fake_fetch)

    events = client.list_events(date=datetime(2025, 1, 1))
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, Event)
    assert ev.id == "1"
    assert ev.title == "Demo"
    assert ev.start_utc == datetime(2025, 1, 1, 1, 0, tzinfo=timezone.utc)
    assert ev.end_utc == datetime(2025, 1, 1, 2, 0, tzinfo=timezone.utc)


def test_list_events_timezone_env(monkeypatch):
    """GoogleClient should respect TIMEZONE environment variable."""

    import importlib

    monkeypatch.setenv("TIMEZONE", "UTC")

    config_module = importlib.import_module("schedule_app.config")
    importlib.reload(config_module)
    google_client_module = importlib.import_module(
        "schedule_app.services.google_client"
    )
    importlib.reload(google_client_module)

    client = google_client_module.GoogleClient(credentials=None)

    captured: dict[str, str] = {}

    def fake_fetch(*, time_min: str, time_max: str) -> list[dict]:
        captured["time_min"] = time_min
        captured["time_max"] = time_max
        return []

    monkeypatch.setattr(client, "fetch_calendar_events", fake_fetch)

    client.list_events(date=datetime(2025, 1, 1))

    assert captured["time_min"] == "2025-01-01T00:00:00Z"
    assert captured["time_max"] == "2025-01-02T00:00:00Z"


