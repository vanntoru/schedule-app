from __future__ import annotations

from datetime import datetime
from flask import Blueprint, abort, jsonify, request

from schedule_app.services import schedule

bp = Blueprint("schedule", __name__, url_prefix="/api/schedule")
schedule_bp = bp


@bp.route("/generate", methods=["GET"])
def generate_schedule():  # noqa: D401 - simple endpoint
    """Generate a schedule grid for the specified date."""
    date_str = request.args.get("date")
    if not date_str:
        abort(400, description="date parameter required")

    tz = schedule._jst()

    if "T" in date_str:
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            abort(400, description="invalid date format")

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)

        local_dt = dt.astimezone(tz)
    else:
        try:
            local_dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            abort(400, description="invalid date format")

        local_dt = local_dt.replace(tzinfo=tz)

    local_day = local_dt.date()

    algo = request.args.get("algo", "greedy")
    if algo not in {"greedy", "compact"}:
        abort(400, description="invalid algo")

    result = schedule.generate_schedule(target_day=local_day, algo=algo)
    result.pop("algo", None)
    result["date"] = local_day.isoformat()

    return jsonify(result)


__all__ = ["bp", "schedule_bp"]
