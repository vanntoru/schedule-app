from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask import Blueprint, abort, jsonify, request

from schedule_app.config import cfg

from schedule_app.services import schedule


bp = Blueprint("schedule", __name__, url_prefix="/api/schedule")
schedule_bp = bp


@bp.route("/generate", methods=["POST"])
def generate_schedule():  # noqa: D401 - simple endpoint
    """Generate a schedule grid for the specified date."""
    date_str = request.args.get("date")
    if not date_str:
        abort(400, description="date parameter required")

    try:
        dt = datetime.fromisoformat(date_str)
    except ValueError:
        abort(400, description="invalid date format")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(cfg.TIMEZONE))

    date_obj = dt.astimezone(timezone.utc)

    algo = request.args.get("algo", "greedy")
    if algo not in {"greedy", "compact"}:
        abort(400, description="invalid algo")

    result = schedule.generate_schedule(target_day=date_obj.date(), algo=algo)
    result.pop("algo", None)
    return jsonify(result)


__all__ = ["bp", "schedule_bp"]
