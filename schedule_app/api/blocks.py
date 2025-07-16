"""
Block CRUD REST API  (/api/blocks …)

依存:
    - schedule_app.models.Block  (UTC 保持の dataclass)
    - Flask 2.3
設置:
    from schedule_app.api.blocks import init_blocks_api
    app = Flask(__name__)
    init_blocks_api(app)
"""

from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from flask import Blueprint, Response, jsonify, request, url_for
from werkzeug.exceptions import BadRequest, NotFound

from schedule_app.models import Block
from schedule_app.config import cfg
from schedule_app.services.google_client import (
    fetch_blocks_from_sheet,
    invalidate_blocks_cache,
)
from schedule_app.exceptions import APIError
from schedule_app.errors import InvalidBlockRow

__all__ = ["blocks_bp", "init_blocks_api"]


# --------------------------------------------------------------------------- #
# 内部ストレージ（単一プロセス想定。必要なら後で DB に置き換え）
# --------------------------------------------------------------------------- #
BLOCKS: dict[str, Block] = {}


# --------------------------------------------------------------------------- #
# 補助関数
# --------------------------------------------------------------------------- #
def _parse_iso8601(value: str, field: str) -> datetime:
    """`2025-01-01T00:00:00Z` → aware UTC datetime."""
    if not isinstance(value, str):
        raise BadRequest(problem_detail(f"{field} must be string"))
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise BadRequest(problem_detail(f"{field} is not RFC 3339")) from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def problem_detail(detail: str, status: int = 422) -> dict[str, Any]:
    """Generate a Problem Details JSON (RFC 9457)."""
    return {
        "type": "https://schedule.app/errors/invalid-field",
        "title": "Validation failed",
        "status": status,
        "detail": detail,
    }


def _block_to_dict(block: Block) -> dict[str, Any]:
    """Dataclass → JSON 変換。datetime は RFC 3339(秒, Z) に整形。"""
    d = asdict(block)
    d["start_utc"] = block.start_utc.replace(tzinfo=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    d["end_utc"] = block.end_utc.replace(tzinfo=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return d


def _load_sheet_blocks() -> list[Block]:
    """Return blocks fetched from Google Sheets."""

    try:
        return fetch_blocks_from_sheet(cfg.BLOCKS_SHEET_ID, cfg.SHEETS_BLOCK_RANGE)
    except InvalidBlockRow:
        raise
    except Exception as exc:  # pragma: no cover - network errors
        raise APIError(str(exc))


# --------------------------------------------------------------------------- #
# Blueprint
# --------------------------------------------------------------------------- #
blocks_bp = Blueprint("blocks", __name__, url_prefix="/api/blocks")


@blocks_bp.get("")
def list_blocks() -> Response:
    """GET /api/blocks → 200 Block[]"""
    return jsonify([_block_to_dict(b) for b in BLOCKS.values()])


@blocks_bp.get("/import")
def import_blocks() -> Response:
    """GET /api/blocks/import → 200 Block[]"""

    blocks = _load_sheet_blocks()
    return jsonify([_block_to_dict(b) for b in blocks])


@blocks_bp.post("/import")
def import_blocks_post() -> Response:
    """POST /api/blocks/import → 204"""

    blocks = _load_sheet_blocks()

    BLOCKS.clear()
    for b in blocks:
        BLOCKS[b.id] = b

    return ("", 204)


@blocks_bp.post("")
def create_block() -> tuple[Response, int, dict[str, str]]:
    """POST /api/blocks → 201 Block + Location"""
    payload = request.get_json(silent=True) or {}
    try:
        start = _parse_iso8601(payload.get("start_utc"), "start_utc")
        end = _parse_iso8601(payload.get("end_utc"), "end_utc")
    except BadRequest as e:
        return jsonify(e.description), 422

    if start >= end:
        return jsonify(problem_detail("start_utc must be earlier than end_utc")), 422

    block_id = uuid.uuid4().hex
    block = Block(id=block_id, start_utc=start, end_utc=end)
    BLOCKS[block_id] = block
    headers = {"Location": url_for("blocks.get_block", id_=block_id, _external=True)}
    return jsonify(_block_to_dict(block)), 201, headers


@blocks_bp.get("/<id_>")
def get_block(id_: str) -> Response:
    """取得（テスト用）"""
    if id_ not in BLOCKS:
        raise NotFound()
    return jsonify(_block_to_dict(BLOCKS[id_]))


@blocks_bp.put("/<id_>")
def update_block(id_: str) -> Response:
    """PUT /api/blocks/<id> → 200 / 404 / 422"""
    if id_ not in BLOCKS:
        raise NotFound()

    payload = request.get_json(silent=True) or {}
    try:
        start = _parse_iso8601(payload.get("start_utc"), "start_utc")
        end = _parse_iso8601(payload.get("end_utc"), "end_utc")
    except BadRequest as e:
        return jsonify(e.description), 422

    if start >= end:
        return jsonify(problem_detail("start_utc must be earlier than end_utc")), 422

    BLOCKS[id_] = Block(id=id_, start_utc=start, end_utc=end)
    return jsonify(_block_to_dict(BLOCKS[id_]))


@blocks_bp.delete("/<id_>")
def delete_block(id_: str) -> Response:
    """DELETE /api/blocks/<id> → 204 / 404"""
    if id_ not in BLOCKS:
        raise NotFound()
    del BLOCKS[id_]
    return ("", 204)


@blocks_bp.delete("/cache")
def clear_blocks_cache() -> tuple[str, int]:
    """Invalidate the Google Sheets blocks cache."""

    try:
        invalidate_blocks_cache()
    except Exception as exc:  # pragma: no cover - unexpected errors
        raise APIError(str(exc))
    return ("", 204)


# --------------------------------------------------------------------------- #
# blueprint 登録用ファサード
# --------------------------------------------------------------------------- #
def init_blocks_api(app) -> None:  # noqa: ANN001
    """Factory Pattern で呼ばれる。アプリに Blueprint を取り付ける。"""
    app.register_blueprint(blocks_bp)
