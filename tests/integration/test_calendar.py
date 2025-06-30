"""
Google Calendar API から予定を取得する `/api/calendar` エンドポイントの
インテグレーションテスト。

要件
- date クエリが 2025-01-01 のとき、UTC 全日内に収まるイベント２件を返す
- Google API 呼び出しは httpretty でモックする
- 仕様準拠の JSON (Event[]) が 200 で返ること
"""

import json

import httpretty
import pytest
from freezegun import freeze_time
from flask import Flask

from schedule_app import create_app  # Flask factory

# ダミーイベント（UTC）
DUMMY_EVENTS = [
    {
        "id": "evt1",
        "summary": "Morning meeting",
        "start": {"dateTime": "2025-01-01T00:30:00Z"},
        "end": {"dateTime": "2025-01-01T01:30:00Z"},
    },
    {
        "id": "evt2",
        "summary": "Evening exercise",
        "start": {"dateTime": "2025-01-01T13:00:00Z"},
        "end": {"dateTime": "2025-01-01T14:00:00Z"},
    },
]


@pytest.fixture(scope="module")
def app() -> Flask:
    return create_app(testing=True)


@freeze_time("2025-01-01T09:00:00Z")
@httpretty.activate(allow_net_connect=False)
def test_get_calendar_events(app):
    """/api/calendar が Google API を呼び出し、正しい JSON を返す"""
    # Google API へのリクエスト URL を粗くパターン一致で登録
    httpretty.register_uri(
        httpretty.GET,
        uri=r"https://www.googleapis.com/calendar/v3/calendars/primary/events.*",
        body=json.dumps({"items": DUMMY_EVENTS}),
        content_type="application/json",
    )

    client = app.test_client()
    res = client.get("/api/calendar?date=2025-01-01")

    assert res.status_code == 200
    data = res.get_json()
    assert len(data) == 2
    evt = data[0]
    # モデル変換後のプロパティを検査
    assert evt["title"] == "Morning meeting"
    assert evt["start_utc"] == "2025-01-01T00:30:00Z"
    assert evt["all_day"] is False
