import importlib
from datetime import datetime, timezone, timedelta

from freezegun import freeze_time
import pytest

import schedule_app.config as config_module


class DummyService:
    def __init__(self, rows):
        self.rows = rows
        self.calls = 0

    def spreadsheets(self):
        return self

    def values(self):
        return self

    def get(self, spreadsheetId, range):  # noqa: D401 - simple stub
        self.calls += 1
        self.spreadsheetId = spreadsheetId
        self.range = range
        return self

    def execute(self):
        return {"values": self.rows}


def _setup(monkeypatch, values, cache_sec=60):
    monkeypatch.setenv("SHEETS_TASKS_SSID", "sheet-id")
    monkeypatch.setenv("SHEETS_TASKS_RANGE", "Tasks!A:G")
    monkeypatch.setenv("SHEETS_CACHE_SEC", str(cache_sec))
    importlib.reload(config_module)
    import schedule_app.services.sheets_tasks as st
    importlib.reload(st)
    service = DummyService(values)
    monkeypatch.setattr(st, "build", lambda *a, **k: service)
    st._CACHE = None
    return st, service


def test_fetch_tasks_basic(monkeypatch):
    rows = [
        [
            "id",
            "title",
            "category",
            "duration_min",
            "duration_raw_min",
            "priority",
            "earliest_start_utc",
        ],
        [
            "t1",
            "Task1",
            "gen",
            "20",
            "25",
            "A",
            "2025-01-01T09:00:00Z",
        ],
        ["t2", "Task2", "gen", "10", "10", "B", ""],
    ]

    st, service = _setup(monkeypatch, rows)
    session = {"credentials": {"access_token": "tok"}}
    tasks = st.fetch_tasks_from_sheet(session, force=True)

    assert service.calls == 1
    assert len(tasks) == 2
    t1 = tasks[0]
    assert t1.id == "t1"
    assert t1.duration_min == 20
    assert t1.duration_raw_min == 25
    assert t1.priority == "A"
    assert t1.earliest_start_utc == datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)
    assert tasks[1].earliest_start_utc is None


def test_fetch_tasks_cache(monkeypatch):
    rows1 = [
        [
            "id",
            "title",
            "category",
            "duration_min",
            "duration_raw_min",
            "priority",
        ],
        ["a", "A", "c", "10", "10", "A"],
    ]

    with freeze_time("2025-01-01T00:00:00Z") as frozen:
        st, service1 = _setup(monkeypatch, rows1, cache_sec=10)
        session = {"credentials": {"access_token": "tok"}}
        tasks1 = st.fetch_tasks_from_sheet(session, force=True)
        assert service1.calls == 1

        rows2 = [["id", "title", "category", "duration_min", "duration_raw_min", "priority"], ["b", "B", "c", "5", "5", "B"]]
        service2 = DummyService(rows2)
        monkeypatch.setattr(st, "build", lambda *a, **k: service2)

        tasks2 = st.fetch_tasks_from_sheet(session)
        assert service2.calls == 0
        assert tasks2 == tasks1

        frozen.tick(delta=timedelta(seconds=11))
        tasks3 = st.fetch_tasks_from_sheet(session)
        assert service2.calls == 1
        assert tasks3 != tasks1


def test_to_task_uuid_and_round(monkeypatch):
    st, _service = _setup(monkeypatch, [])

    data = {
        "id": "",
        "title": "T",
        "category": "c",
        "duration_min": "25",
        "duration_raw_min": "25",
        "priority": "A",
    }

    task = st._to_task(data)
    assert task.id
    assert task.duration_min == 30
    assert task.duration_raw_min == 25


def test_to_task_priority_error(monkeypatch):
    st, _ = _setup(monkeypatch, [])
    with pytest.raises(st.InvalidSheetRowError):
        st._to_task({"priority": "C", "duration_min": "10", "duration_raw_min": "10"})


def test_to_task_invalid_datetime(monkeypatch):
    st, _ = _setup(monkeypatch, [])
    with pytest.raises(st.InvalidSheetRowError):
        st._to_task({"priority": "A", "duration_min": "10", "duration_raw_min": "10", "earliest_start_utc": "bad"})


@pytest.mark.parametrize("val", ["9", "-5"])
def test_to_task_invalid_duration(monkeypatch, val):
    st, _ = _setup(monkeypatch, [])
    with pytest.raises(st.InvalidSheetRowError):
        st._to_task({"priority": "A", "duration_min": val, "duration_raw_min": val})
