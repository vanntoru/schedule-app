# tests/integration/test_calendar.py
# GET /api/calendar の正常系・異常系を検証するテストを生成してください。
#
# 依存:
# - pytest
# - freezegun
# - flask.testing.FlaskClient
#
# テスト観点
# 1. date クエリ欠如 → 400
# 2. date フォーマット不正 → 400
# 3. 正常系:
#    - モック GoogleClient.list_events が Event を 1 件返す
#    - HTTP 200, JSON 長さ 1, id/title が一致
# 4. Google 認可無し (UnauthorizedError 仮定) → 401
#
# 実装ヒント
# - app.test_client() を fixture にする
# - monkeypatch で current_app.extensions["gclient"] をダミークラスに差し替える
# - freezegun.freeze_time("2025-01-01T00:00:00Z") でタイムゾーン影響を固定
#
# 生成するテストコードだけを出力してください。

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pytest
from freezegun import freeze_time
from flask import current_app

from schedule_app import create_app
from schedule_app.models import Event


class UnauthorizedError(Exception):
    """Dummy exception for unauthorized access."""


@dataclass
class DummyGoogleClient:
    events: list[Event] | None = None
    raise_unauth: bool = False

    def list_events(self, *, date: datetime) -> list[Event]:
        if self.raise_unauth:
            raise UnauthorizedError("unauthorized")
        return self.events or []


@pytest.fixture()
def app() -> Any:
    app = create_app(testing=True)
    return app


@pytest.fixture()
def client(app: Any):
    return app.test_client()


def _install_dummy(app: Any, dummy: DummyGoogleClient) -> None:
    with app.app_context():
        current_app.extensions["gclient"] = dummy


def test_missing_date_returns_400(app: Any, client: Any) -> None:
    _install_dummy(app, DummyGoogleClient())
    resp = client.get("/api/calendar")
    assert resp.status_code == 400


def test_invalid_date_format_returns_400(app: Any, client: Any) -> None:
    _install_dummy(app, DummyGoogleClient())
    resp = client.get("/api/calendar?date=bad-date")
    assert resp.status_code == 400


@freeze_time("2025-01-01T00:00:00Z")
def test_get_calendar_success(app: Any, client: Any) -> None:
    event = Event(
        id="evt1",
        start_utc=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
        end_utc=datetime(2025, 1, 1, 1, 0, tzinfo=timezone.utc),
        title="Test Event",
    )
    dummy = DummyGoogleClient(events=[event])
    _install_dummy(app, dummy)

    resp = client.get("/api/calendar?date=2025-01-01")
    assert resp.status_code == 200

    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == event.id
    assert data[0]["title"] == event.title


def test_get_calendar_unauthorized(app: Any, client: Any) -> None:
    dummy = DummyGoogleClient(raise_unauth=True)
    _install_dummy(app, dummy)
    resp = client.get("/api/calendar?date=2025-01-01")
    assert resp.status_code == 401
