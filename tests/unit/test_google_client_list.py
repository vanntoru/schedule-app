from datetime import datetime

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

    assert captured["time_min"] == "2025-01-01T00:00:00Z"
    assert captured["time_max"] == "2025-01-02T00:00:00Z"


