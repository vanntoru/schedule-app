import os
from dataclasses import dataclass
from functools import lru_cache

@dataclass(slots=True, frozen=True)
class Settings:
    """アプリ全体で共有する設定値（読み取り専用）"""
    google_client_id: str
    google_client_secret: str
    secret_key: str
    timezone: str = "Asia/Tokyo"

@lru_cache
def get_settings() -> Settings:
    """環境変数を読み込んで Settings を返す（キャッシュ付き）"""
    missing = [k for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "SECRET_KEY")
               if k not in os.environ]
    if missing:
        raise RuntimeError(f"Missing env vars: {', '.join(missing)}")

    return Settings(
        google_client_id=os.environ["GOOGLE_CLIENT_ID"],
        google_client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        secret_key=os.environ["SECRET_KEY"],
    )
