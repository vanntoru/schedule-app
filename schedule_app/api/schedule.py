from __future__ import annotations

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo
from flask import Blueprint, abort, jsonify, request

from schedule_app.services import schedule
from schedule_app.config import cfg

JST = ZoneInfo(cfg.TIMEZONE)


bp = Blueprint("schedule", __name__, url_prefix="/api/schedule")
schedule_bp = bp


@bp.route("/generate", methods=["POST", "GET"])
def generate_schedule():  # noqa: D401 - simple endpoint
    """Generate a schedule grid for the specified date."""
    date_str = request.args.get("date")
    if not date_str:
        abort(400, description="date parameter required")

    if "T" in date_str:
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            abort(400, description="invalid date format")
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=JST)
        local_day = dt.astimezone(JST).date()
    else:
        try:
            local_day = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            abort(400, description="invalid date format")

    target_day_utc = (
        datetime.combine(local_day, time.min, tzinfo=JST).astimezone(timezone.utc)
    )

    algo = request.args.get("algo", "greedy")
    if algo not in {"greedy", "compact"}:
        abort(400, description="invalid algo")

    result = schedule.generate_schedule(target_day=target_day_utc.date(), algo=algo)
    result.pop("algo", None)
    result["date"] = local_day.isoformat()
    return jsonify(result)


__all__ = ["bp", "schedule_bp"]
