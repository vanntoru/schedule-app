import json
from datetime import datetime, timedelta, timezone
from io import BytesIO

from freezegun import freeze_time
import pytest


def _setup(monkeypatch, values, cache_sec=60):
    monkeypatch.setenv("BLOCKS_SHEET_ID", "sheet-id")
    monkeypatch.setenv("SHEETS_BLOCK_RANGE", "Blocks!A2:C")
    monkeypatch.setenv("SHEETS_CACHE_SEC", str(cache_sec))
    import schedule_app.services.google_client as gc
    gc._BLOCK_CACHE = None

    data = {"values": values}

    class DummyResp(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

    def fake_urlopen(req):
        return DummyResp(json.dumps(data).encode())

    monkeypatch.setattr(gc.request, "urlopen", fake_urlopen)
    return gc


def test_fetch_blocks_basic(monkeypatch):
    rows = [
        ["id", "start_utc", "end_utc", "title"],
        ["b1", "2025-01-01T00:00:00Z", "2025-01-01T01:00:00Z", "B"],
    ]
    gc = _setup(monkeypatch, rows)
    session = {"credentials": {"access_token": "tok"}}
    blocks = gc.fetch_blocks_from_sheet(session, force=True)
    assert len(blocks) == 1
    blk = blocks[0]
    assert blk.id == "b1"
    assert blk.start_utc == datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    assert blk.title == "B"


def test_fetch_blocks_cache(monkeypatch):
    rows1 = [["id", "start_utc", "end_utc"], ["a", "2025-01-01T00:00:00Z", "2025-01-01T01:00:00Z"]]
    with freeze_time("2025-01-01T00:00:00Z") as frozen:
        gc = _setup(monkeypatch, rows1, cache_sec=10)
        session = {"credentials": {"access_token": "tok"}}
        blocks1 = gc.fetch_blocks_from_sheet(session, force=True)

        rows2 = [["id", "start_utc", "end_utc"], ["b", "2025-01-01T02:00:00Z", "2025-01-01T03:00:00Z"]]
        data2 = {"values": rows2}

        class Resp(BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                pass

        def second_call(req):
            return Resp(json.dumps(data2).encode())

        monkeypatch.setattr(gc.request, "urlopen", second_call)
        blocks2 = gc.fetch_blocks_from_sheet(session)
        assert blocks2 == blocks1

        frozen.tick(delta=timedelta(seconds=11))
        blocks3 = gc.fetch_blocks_from_sheet(session)
        assert blocks3 != blocks1


def test_invalid_block_row(monkeypatch):
    rows = [["start_utc", "end_utc"], ["", "2025-01-01T01:00:00Z"]]
    gc = _setup(monkeypatch, rows)
    session = {"credentials": {"access_token": "tok"}}
    with pytest.raises(gc.InvalidBlockRow):
        gc.fetch_blocks_from_sheet(session, force=True)
