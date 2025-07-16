import importlib

import schedule_app.config as config_module


def test_defaults(monkeypatch):
    monkeypatch.delenv("SHEETS_TASKS_SSID", raising=False)
    monkeypatch.delenv("SHEETS_TASKS_RANGE", raising=False)
    monkeypatch.delenv("SHEETS_CACHE_SEC", raising=False)
    monkeypatch.delenv("BLOCKS_SHEET_ID", raising=False)
    monkeypatch.delenv("SHEETS_BLOCK_RANGE", raising=False)

    # Reload module to apply env changes
    importlib.reload(config_module)
    cfg = config_module.cfg

    assert cfg.SHEETS_TASKS_RANGE == "Tasks!A:F"
    assert cfg.SHEETS_CACHE_SEC == 300
    assert cfg.SHEETS_TASKS_SSID is None
    assert cfg.BLOCKS_SHEET_ID is None
    assert cfg.SHEETS_BLOCK_RANGE == "Blocks!A2:C"
