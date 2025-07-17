"""Integration tests for /api/blocks/import using HTTP stubs."""

from __future__ import annotations

import importlib
import json
from urllib.parse import quote

import httpretty
import pytest
from flask import Flask

from schedule_app import create_app


@pytest.fixture()
def app(monkeypatch) -> Flask:
    monkeypatch.setenv("BLOCKS_SHEET_ID", "sheet-id")
    monkeypatch.setenv("SHEETS_BLOCK_RANGE", "Blocks!A2:C")

    import schedule_app.config as config_module
    importlib.reload(config_module)

    import schedule_app.services.google_client as gc
    gc.config_module = config_module
    gc._BLOCK_CACHE = None

    flask_app = create_app(testing=True)
    return flask_app


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


def _sheet_url() -> str:
    encoded = quote("Blocks!A2:C", safe="")
    return f"https://sheets.googleapis.com/v4/spreadsheets/sheet-id/values/{encoded}"


def _assert_problem_details(data) -> None:
    assert isinstance(data, dict)
    for key in ("type", "title", "status"):
        assert key in data


@httpretty.activate
def test_import_blocks_get_success(client) -> None:
    url = _sheet_url()
    body = {
        "values": [
            ["start_utc", "end_utc"],
            ["2025-01-01T00:00:00Z", "2025-01-01T00:10:00Z"],
        ]
    }
    httpretty.register_uri(httpretty.GET, url, body=json.dumps(body), content_type="application/json")

    resp = client.get("/api/blocks/import")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 1


@httpretty.activate
def test_import_blocks_post_success(client) -> None:
    url = _sheet_url()
    body = {
        "values": [
            ["start_utc", "end_utc"],
            ["2025-01-01T01:00:00Z", "2025-01-01T01:10:00Z"],
        ]
    }
    httpretty.register_uri(httpretty.GET, url, body=json.dumps(body), content_type="application/json")

    resp = client.post("/api/blocks/import")
    assert resp.status_code == 204


@httpretty.activate
def test_import_blocks_invalid_row(client) -> None:
    url = _sheet_url()
    body = {
        "values": [
            ["start_utc", "end_utc"],
            ["bad", "2025-01-01T00:10:00Z"],
        ]
    }
    httpretty.register_uri(httpretty.GET, url, body=json.dumps(body), content_type="application/json")

    resp = client.get("/api/blocks/import")
    assert resp.status_code == 422
    _assert_problem_details(resp.get_json())


@httpretty.activate
def test_import_blocks_api_error(client) -> None:
    url = _sheet_url()
    httpretty.register_uri(httpretty.GET, url, status=500)

    resp = client.post("/api/blocks/import")
    assert resp.status_code == 502
    _assert_problem_details(resp.get_json())
