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

    # accept plain dates or datetimes with optional trailing 'Z'
    if date_str.endswith("Z"):
        date_str = date_str[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(date_str)
    except ValueError:
        abort(400, description="invalid date format")

    local_day = dt.date()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    date_utc = dt.astimezone(timezone.utc)

    algo = request.args.get("algo", "greedy")
    if algo not in {"greedy", "compact"}:
        abort(400, description="invalid algo")

    result = schedule.generate_schedule(target_day=date_utc.date(), algo=algo)
    result.pop("algo", None)
    result["date"] = local_day.isoformat()
    return jsonify(result)


__all__ = ["bp", "schedule_bp"]
