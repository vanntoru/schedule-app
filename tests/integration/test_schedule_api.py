# ruff: noqa: E402
from __future__ import annotations

import os
import pytest
from flask import Flask

# ---------------------------------------------------------------------------
# Prep dummy env vars so create_app() works without real GCP creds
# ---------------------------------------------------------------------------
os.environ.setdefault("GCP_PROJECT", "dummy-project")
os.environ.setdefault("GOOGLE_CLIENT_ID", "dummy-client-id")

@pytest.fixture()
def app() -> Flask:
    from schedule_app import create_app

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


def test_generate_localizes_naive_datetime(client) -> None:
    """Naive datetimes are interpreted using cfg.TIMEZONE."""
    from datetime import datetime, timezone
    from unittest.mock import patch
    import pytz
    from schedule_app.config import cfg

    fake_result = {"date": "2025-01-01", "algo": "greedy", "slots": [0] * 144, "unplaced": []}
    with patch("schedule_app.api.schedule.schedule.generate_schedule", return_value=fake_result) as mock_gen:
        resp = client.post("/api/schedule/generate?date=2025-01-01T00:00:00")
        assert resp.status_code == 200
        mock_gen.assert_called_once()
        target_day = mock_gen.call_args.kwargs["target_day"]
        tz = pytz.timezone(cfg.TIMEZONE)
        dt = tz.localize(datetime(2025, 1, 1, 0, 0))
        assert target_day == dt.astimezone(timezone.utc).date()
