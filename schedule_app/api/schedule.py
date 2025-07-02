from __future__ import annotations

from datetime import datetime, timezone
from flask import Blueprint, abort, jsonify, request

from schedule_app.services import schedule


bp = Blueprint("schedule", __name__, url_prefix="/api/schedule")
schedule_bp = bp


@bp.route("/generate", methods=["POST", "GET"])
def generate_schedule():  # noqa: D401 - simple endpoint
    """Generate a schedule grid for the specified date."""
    date_str = request.args.get("date")
    if not date_str:
        abort(400, description="date parameter required")
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        abort(400, description="invalid date format")

    algo = request.args.get("algo", "greedy")
    if algo not in {"greedy", "compact"}:
        abort(400, description="invalid algo")

    result = schedule.generate_schedule(target_day=date_obj.date(), algo=algo)
    result.pop("algo", None)
    return jsonify(result)


__all__ = ["bp", "schedule_bp"]
