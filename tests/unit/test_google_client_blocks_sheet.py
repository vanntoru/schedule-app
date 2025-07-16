import importlib
import json
from datetime import datetime, timezone, timedelta

import pytest
from freezegun import freeze_time

import schedule_app.services.google_client as gc


class DummyResponse:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass

    def read(self):
        return json.dumps({"values": self.rows}).encode()


def _setup(monkeypatch, rows):
    importlib.reload(gc)

    def dummy_open(url):
        dummy_open.calls += 1
        return DummyResponse(rows)

    dummy_open.calls = 0
    monkeypatch.setattr(gc, "request.urlopen", dummy_open)
    gc._BLOCK_CACHE = None
    return dummy_open


def test_fetch_blocks_basic(monkeypatch):
    rows = [
        ["2025-01-01T09:03:00Z", "2025-01-01T10:23:00Z", "Morning"],
        ["2025-01-01T11:10:00Z", "2025-01-01T11:20:00Z", ""],
    ]
    opener = _setup(monkeypatch, rows)
    blocks = gc.fetch_blocks_from_sheet("sid", "Blocks!A2:C")

    assert opener.calls == 1
    assert len(blocks) == 2
    b0 = blocks[0]
    assert b0.start_utc == datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)
    assert b0.end_utc == datetime(2025, 1, 1, 10, 30, tzinfo=timezone.utc)
    assert b0.title == "Morning"
    assert blocks[1].title is None


def test_fetch_blocks_cache(monkeypatch):
    rows1 = [["2025-01-01T01:00:00Z", "2025-01-01T02:00:00Z"]]
    with freeze_time("2025-01-01T00:00:00Z") as frozen:
        opener1 = _setup(monkeypatch, rows1)
        blocks1 = gc.fetch_blocks_from_sheet("sid", "Blocks!A2:C")
        assert opener1.calls == 1

        rows2 = [["2025-01-01T03:00:00Z", "2025-01-01T04:00:00Z"]]
        opener2 = _setup(monkeypatch, rows2)
        blocks2 = gc.fetch_blocks_from_sheet("sid", "Blocks!A2:C")
        assert opener2.calls == 0
        assert blocks2 == blocks1

        frozen.tick(delta=timedelta(seconds=301))
        blocks3 = gc.fetch_blocks_from_sheet("sid", "Blocks!A2:C")
        assert opener2.calls == 1
        assert blocks3 != blocks1


def test_fetch_blocks_invalid_row(monkeypatch):
    rows = [["2025-01-01T03:00:00Z", "2025-01-01T02:00:00Z"]]
    _setup(monkeypatch, rows)
    with pytest.raises(gc.InvalidBlockRow):
        gc.fetch_blocks_from_sheet("sid", "Blocks!A2:C")
