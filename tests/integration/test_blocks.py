"""
統合テスト: Block CRUD API
pytest -q tests/integration/test_blocks.py
"""

from __future__ import annotations


import pytest
from flask import Flask

from schedule_app import create_app as create_flask_app  # factory 関数を想定


@pytest.fixture()
def app() -> Flask:
    """テスト用 Flask アプリ"""
    app = create_flask_app(testing=True)
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def iso(dt: str) -> str:
    """短縮ヘルパ: '2025‑01‑01T02:00' → RFC3339 Z 付き"""
    return f"{dt}:00Z"


def _assert_problem_details(data) -> None:
    assert isinstance(data, dict)
    for key in ("type", "title", "status"):
        assert key in data


def test_block_crud_cycle(client):
    # ---------- POST ----------
    resp = client.post(
        "/api/blocks",
        json={
            "start_utc": iso("2025-01-01T02:00"),
            "end_utc": iso("2025-01-01T03:00"),
        },
    )
    assert resp.status_code == 201
    loc = resp.headers["Location"]
    block_id = loc.rsplit("/", 1)[-1]

    # ---------- GET list ----------
    resp = client.get("/api/blocks")
    data = resp.get_json()
    assert resp.status_code == 200
    assert len(data) == 1
    assert data[0]["id"] == block_id

    # ---------- PUT ----------
    resp = client.put(
        f"/api/blocks/{block_id}",
        json={
            "start_utc": iso("2025-01-01T01:30"),
            "end_utc": iso("2025-01-01T03:00"),
        },
    )
    assert resp.status_code == 200
    assert resp.get_json()["start_utc"].startswith("2025-01-01T01:30")

    # ---------- DELETE ----------
    resp = client.delete(f"/api/blocks/{block_id}")
    assert resp.status_code == 204

    # ---------- GET list again ----------
    resp = client.get("/api/blocks")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_import_blocks_success(client, monkeypatch):
    from schedule_app.models import Block
    from datetime import datetime, timezone

    sample_blocks = [
        Block(id="b1", start_utc=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc), end_utc=datetime(2025, 1, 1, 0, 10, tzinfo=timezone.utc))
    ]

    monkeypatch.setattr(
        "schedule_app.api.blocks.fetch_blocks_from_sheet",
        lambda *a, **k: sample_blocks,
    )

    resp = client.get("/api/blocks/import")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == "b1"


def test_import_blocks_invalid_row(client, monkeypatch):
    from schedule_app.errors import InvalidBlockRow

    def raise_error(*a, **k):
        raise InvalidBlockRow()

    monkeypatch.setattr("schedule_app.api.blocks.fetch_blocks_from_sheet", raise_error)

    resp = client.get("/api/blocks/import")
    assert resp.status_code == 422
    _assert_problem_details(resp.get_json())


def test_import_blocks_api_error(client, monkeypatch):
    def boom(*a, **k):
        raise Exception("boom")

    monkeypatch.setattr("schedule_app.api.blocks.fetch_blocks_from_sheet", boom)

    resp = client.get("/api/blocks/import")
    assert resp.status_code == 502
    _assert_problem_details(resp.get_json())


def _create_sample_block(client) -> str:
    resp = client.post(
        "/api/blocks",
        json={
            "start_utc": iso("2025-01-01T01:00"),
            "end_utc": iso("2025-01-01T01:10"),
        },
    )
    return resp.get_json()["id"]


def test_import_blocks_post_replace(client, monkeypatch):
    old_id = _create_sample_block(client)

    from schedule_app.models import Block
    from datetime import datetime, timezone

    new_blocks = [
        Block(
            id="n1",
            start_utc=datetime(2025, 1, 1, 2, 0, tzinfo=timezone.utc),
            end_utc=datetime(2025, 1, 1, 2, 10, tzinfo=timezone.utc),
        )
    ]

    monkeypatch.setattr(
        "schedule_app.api.blocks.fetch_blocks_from_sheet",
        lambda *a, **k: new_blocks,
    )

    resp = client.post("/api/blocks/import")
    assert resp.status_code == 204

    resp = client.get("/api/blocks")
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["id"] == "n1"
    assert data[0]["id"] != old_id


def test_import_blocks_post_validation_error(client, monkeypatch):
    old_id = _create_sample_block(client)

    from schedule_app.errors import InvalidBlockRow

    monkeypatch.setattr(
        "schedule_app.api.blocks.fetch_blocks_from_sheet",
        lambda *a, **k: (_ for _ in ()).throw(InvalidBlockRow()),
    )

    resp = client.post("/api/blocks/import")
    assert resp.status_code == 422
    _assert_problem_details(resp.get_json())

    resp = client.get("/api/blocks")
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["id"] == old_id


def test_import_blocks_post_api_error(client, monkeypatch):
    old_id = _create_sample_block(client)

    def boom(*a, **k):
        raise Exception("boom")

    monkeypatch.setattr("schedule_app.api.blocks.fetch_blocks_from_sheet", boom)

    resp = client.post("/api/blocks/import")
    assert resp.status_code == 502
    _assert_problem_details(resp.get_json())

    resp = client.get("/api/blocks")
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["id"] == old_id
