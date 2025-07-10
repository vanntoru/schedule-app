import importlib
import os

import schedule_app.config as config_module


def test_defaults(monkeypatch):
    monkeypatch.delenv("SHEETS_TASKS_SSID", raising=False)
    monkeypatch.delenv("SHEETS_TASKS_RANGE", raising=False)
    monkeypatch.delenv("SHEETS_CACHE_SEC", raising=False)

    # Reload module to apply env changes
    importlib.reload(config_module)
    cfg = config_module.cfg

    assert cfg.SHEETS_TASKS_RANGE == "Tasks!A:F"
    assert cfg.SHEETS_CACHE_SEC == 300
    assert cfg.SHEETS_TASKS_SSID is None
