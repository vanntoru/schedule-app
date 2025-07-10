# schedule_app/config.py
"""
環境変数 → Python オブジェクトへ集約
----------------------------------
❶ `.env` ファイル（開発用）
❷ OS 環境変数（本番用）
の順に読み取り、存在しない場合はデフォルト値を入れる。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    # 開発環境では .env があれば自動読み込み
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # prod (Cloud Run) では python-dotenv を入れない想定
    pass


@dataclass(slots=True, frozen=True)
class _Config:
    # --- Flask ---
    DEBUG: bool = os.getenv("FLASK_DEBUG", "0") == "1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "please-change-me")

    # --- Google Cloud ---
    GCP_PROJECT: str = os.environ["GCP_PROJECT"]
    GCP_REGION: str = os.getenv("GCP_REGION", "asia-northeast1")

    # --- OAuth ---
    GOOGLE_CLIENT_ID: str = os.environ["GOOGLE_CLIENT_ID"]
    GOOGLE_CLIENT_SECRET: str | None = os.getenv("GOOGLE_CLIENT_SECRET")  # PKCEでは不要
    OAUTH_REDIRECT_URI: str = os.getenv(
        "OAUTH_REDIRECT_URI",
        "http://localhost:5173/oauth2callback",
    )

    # --- App Settings ---
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Tokyo")
    SLOT_SEC: int = int(os.getenv("SLOT_SEC", "600"))  # 10min

    # --- Google Sheets ---
    SHEETS_TASKS_SSID: str | None = os.getenv("SHEETS_TASKS_SSID")
    SHEETS_TASKS_RANGE: str = os.getenv("SHEETS_TASKS_RANGE", "Tasks!A:F")
    SHEETS_CACHE_SEC: int = int(os.getenv("SHEETS_CACHE_SEC", "300"))

    # 追加があった場合はここへ…

    # ---- パス系（自動計算） ----
    BASE_DIR: Path = Path(__file__).resolve().parent.parent


# アプリ全体が使うシングルトン
cfg = _Config()
