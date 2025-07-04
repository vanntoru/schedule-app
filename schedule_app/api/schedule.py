from __future__ import annotations

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo
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
        # 入力文字列は JST 日付と解釈
        local_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        abort(400, description="invalid date format")

    # JST 00:00 → UTC へ変換し、その日付 (=UTC 日) をアルゴリズムに渡す
    JST = ZoneInfo("Asia/Tokyo")
    local_start = datetime.combine(local_date, time.min, tzinfo=JST)
    target_day_utc = local_start.astimezone(timezone.utc).date()

    algo = request.args.get("algo", "greedy")
    if algo not in {"greedy", "compact"}:
        abort(400, description="invalid algo")

    result = schedule.generate_schedule(target_day=target_day_utc, algo=algo)
    result.pop("algo", None)
    result["date"] = local_date.isoformat()
    return jsonify(result)


__all__ = ["bp", "schedule_bp"]
