import json


class DummyResponse:
    def __init__(self, data: dict) -> None:
        self._data = json.dumps(data).encode()

    def read(self) -> bytes:  # pragma: no cover - simple stub
        return self._data

    def __enter__(self) -> "DummyResponse":  # pragma: no cover - simple stub
        return self

    def __exit__(self, *exc):  # pragma: no cover - simple stub
        return False


def _setup(monkeypatch, rows):
    import importlib
    import schedule_app.config as config_module

    monkeypatch.setenv("BLOCKS_SHEET_ID", "sheet-id")
    monkeypatch.setenv("SHEETS_BLOCK_RANGE", "Blocks!A2:C")
    monkeypatch.setenv("SHEETS_CACHE_SEC", "60")

    importlib.reload(config_module)

    import schedule_app.services.google_client as gc

    gc.config_module = config_module
    gc._BLOCK_CACHE = None
    monkeypatch.setattr(gc.request, "urlopen", lambda req: DummyResponse({"values": rows}))

    return gc


def test_setup_reload(monkeypatch):
    gc = _setup(monkeypatch, [])
    assert gc.config_module.cfg.BLOCKS_SHEET_ID == "sheet-id"
    assert gc._BLOCK_CACHE is None
