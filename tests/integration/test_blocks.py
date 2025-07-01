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
