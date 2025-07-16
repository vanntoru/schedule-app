import json
import importlib
from datetime import datetime, timezone, timedelta

from freezegun import freeze_time


class DummyResponse:
    def __init__(self, data: dict) -> None:
        self._data = json.dumps(data).encode()

    def read(self) -> bytes:  # pragma: no cover - simple stub
        return self._data

    def __enter__(self) -> "DummyResponse":  # pragma: no cover - simple stub
        return self

    def __exit__(self, *exc):  # pragma: no cover - simple stub
        return False


def _setup(monkeypatch, rows, cache_sec=60):
    import schedule_app.config as config_module

    monkeypatch.setenv("BLOCKS_SHEET_ID", "sheet-id")
    monkeypatch.setenv("SHEETS_BLOCK_RANGE", "Blocks!A2:C")
    monkeypatch.setenv("SHEETS_CACHE_SEC", str(cache_sec))

    importlib.reload(config_module)

    import schedule_app.services.google_client as gc

    gc.config_module = config_module
    gc._BLOCK_CACHE = None

    class DummyURL:
        def __init__(self, rows):
            self.rows = rows
            self.calls = 0

        def __call__(self, req):  # pragma: no cover - simple stub
            self.calls += 1
            return DummyResponse({"values": self.rows})

    service = DummyURL(rows)
    monkeypatch.setattr(gc.request, "urlopen", service)

    return gc, service


def test_setup_reload(monkeypatch):
    gc, _service = _setup(monkeypatch, [])
    assert gc.config_module.cfg.BLOCKS_SHEET_ID == "sheet-id"
    assert gc._BLOCK_CACHE is None


def test_fetch_blocks_basic(monkeypatch):
    rows = [
        ["start_utc", "end_utc", "title"],
        ["2025-01-01T00:03:00Z", "2025-01-01T00:31:00Z", "B1"],
        ["2025-01-01T01:00:00", "2025-01-01T01:10:00", ""],
    ]

    gc, service = _setup(monkeypatch, rows)
    blocks = gc.fetch_blocks_from_sheet("sheet-id", "Blocks!A2:C")

    assert service.calls == 1
    assert len(blocks) == 2
    b1 = blocks[0]
    assert b1.start_utc == datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    assert b1.end_utc == datetime(2025, 1, 1, 0, 40, tzinfo=timezone.utc)
    assert b1.title == "B1"
    assert blocks[1].title is None


def test_fetch_blocks_cache(monkeypatch):
    rows1 = [["start_utc", "end_utc"], ["2025-01-01T00:00:00Z", "2025-01-01T00:10:00Z"]]

    with freeze_time("2025-01-01T00:00:00Z") as frozen:
        gc, service1 = _setup(monkeypatch, rows1, cache_sec=10)
        blocks1 = gc.fetch_blocks_from_sheet("sheet-id", "Blocks!A2:C")
        assert service1.calls == 1

        rows2 = [
            ["start_utc", "end_utc"],
            ["2025-01-01T01:00:00Z", "2025-01-01T01:10:00Z"],
        ]

        class DummyURL:
            def __init__(self, rows):
                self.rows = rows
                self.calls = 0

            def __call__(self, req):  # pragma: no cover - simple stub
                self.calls += 1
                return DummyResponse({"values": self.rows})

        service2 = DummyURL(rows2)
        monkeypatch.setattr(gc.request, "urlopen", service2)

        blocks2 = gc.fetch_blocks_from_sheet("sheet-id", "Blocks!A2:C")
        assert service2.calls == 0
        assert blocks2 == blocks1

        frozen.tick(delta=timedelta(seconds=11))
        blocks3 = gc.fetch_blocks_from_sheet("sheet-id", "Blocks!A2:C")
        assert service2.calls == 1
        assert blocks3 != blocks1
