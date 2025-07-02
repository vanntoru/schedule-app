title: 1‑Day Schedule Generator — Web Application
version: v3.0 (LTS / no‑Docker / venv edition)
status: FINAL
last\_updated: 2025‑06‑27
editors: codex & ChatGPT‑o3
---------------------------

# 0. はじめに — “コードを書かずに実装”の前提

* **codex エージェント**は設計書を基にファイルを生成・編集・テストし、Git へコミットする AI アシスタント。
* 本書は **エージェントへの完全指示書**。開発者はクリック／コピペのみで済む。
* **絶対ルール**: Dockerfile を書かない。Windows + VS Code + venv だけで完結。

---

# 1. 目的 / Scope

Google カレンダー予定・ユーザー入力タスク・ブロック（禁止時間帯）を **10 分グリッド**で統合し、印刷および PWA オフライン閲覧可能な **1 日スケジュール** を自動生成・編集できる **シングルユーザー向け Web アプリ** を提供する。

---

# 2. 非機能要件

| 要件       | 内容                                          |
| -------- | ------------------------------------------- |
| 学習コスト    | コマンドはすべてコピペ可能                               |
| 可搬性      | Windows 10/11 64bit + Chrome 最新 + VS Code   |
| 保守性      | Python 3.11 LTS / ES Modules / dataclass 統一 |
| 性能       | p95 応答 < 400 ms、未配置タスク率 < 3 %               |
| アクセシビリティ | WCAG 2.2 AA                                 |

---

# 3. 全体アーキテクチャ

```
┌─────────────┐    HTTPS+JSON    ┌──────────────────┐
│  Front‑end  │  ←────────────── │  Flask REST API  │
│ (Tailwind)  │                  │  (schedule_app)  │
└─────────────┘                  └──────────────────┘
        ▲  ▲                               ▲
        │  │ OAuth2 PKCE                   │
        │  │                               │ Google Calendar
  IndexedDB│                               │ Google Sheets
 (offline) │                               │ Cloud Logging
        ▼  ▼                               ▼
──────────────────────────────────────────────────────────
      Cloud Run (Buildpacks) / Cloud Storage / SecretMgr
```

* **認証**: Google OAuth 2.0 PKCE (S256)
* **データ一次ソース**: Google Calendar / Google Sheets
* **ブラウザ永続**: IndexedDB (`schedule_app`, ver 2)
* **バックエンド**: Flask 2.3 + `google‑api‑python‑client` + `google‑auth`

---

# 4. 開発環境（Windows + VS Code + venv）

```powershell
git clone https://github.com/your-org/schedule-app.git
cd schedule-app
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -U pip
pip install -r requirements.dev.txt
pre-commit install
flask --app schedule_app run --debug --port 5173
```

VS Code は `.vscode/settings.json` により自動で `.venv` を認識。

---

# 5. データモデル (`schedule_app/models.py`)

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

@dataclass(slots=True, frozen=True)
class Event:
    id: str
    start_utc: datetime
    end_utc: datetime
    title: str
    all_day: bool = False

@dataclass(slots=True, frozen=True)
class Task:
    id: str
    title: str
    category: str
    duration_min: int          # 10 分丸め
    duration_raw_min: int      # 入力そのまま (5 分刻み可)
    priority: Literal["A", "B"]
    earliest_start_utc: datetime | None = None

@dataclass(slots=True, frozen=True)
class Block:
    id: str
    start_utc: datetime
    end_utc: datetime
```

---

# 6. REST API v1（Problem Details 準拠）

| Method | Path                                                            | 成功           | 失敗                          |
| ------ | --------------------------------------------------------------- | ------------ | --------------------------- |
| GET    | `/api/calendar?date={2025-01-01T09:00:00+09:00\|YYYY‑MM‑DD}`    | 200 Event\[] | 400 / 401 / 403 / 404 / 500 / 502 |
| GET    | `/api/tasks`                                                    | 200 Task\[]  | –                           |
| POST   | `/api/tasks`                                                    | 201 Task     | 422 invalid‑field           |
| PUT    | `/api/tasks/{id}`                                               | 200 Task     | 404 / 422                   |
| DELETE | `/api/tasks/{id}`                                               | 204          | 404                         |
| GET    | `/api/blocks`                                                   | 200 Block\[] | –                           |
| POST   | `/api/blocks`                                                   | 201 Block    | 422                         |
| PUT    | `/api/blocks/{id}`                                              | 200 Block    | 404 / 422                   |
| DELETE | `/api/blocks/{id}`                                              | 204          | 404                         |
| POST   | `/api/schedule/generate?date=YYYY‑MM‑DD&algo={greedy\|compact}` | 200 Grid     | 400 / 422                   |

*`date` は ISO‑8601 日時 (例: `2025-01-01T09:00:00+09:00`) または `YYYY‑MM‑DD` を受け付け、値は `list_events` 呼び出し前に UTC へ正規化される。*
*Google Calendar API が失敗した場合は 502 Bad Gateway として応答する。*
*認証情報が欠如・期限切れ・取り消しの場合は 401 Unauthorized を返す。*
*Problem Details 例*

```json
{
  "type": "https://schedule.app/errors/invalid-field",
  "title": "Validation failed",
  "status": 422,
  "detail": "Duration must be a positive multiple of 5 minutes.",
  "instance": "/api/tasks/123e4567-e89b-12d3-a456-426614174000"
}
```

---

# 7. スケジュール生成アルゴリズム

1. **量子化**: 10 分 (600 s) ⇒ 1 日 144 slot
2. **busy** = Google Calendar events ∪ blocks
3. **タスクソート key** = `(priority == "A" ? 0 : 1, earliest_start_utc or MIN, -duration_min)`
4. **greedy 配置**: 空き連続 slot に順番に詰める
5. **compact ヒューリスティクス**: 空隙 > 20 min なら再配置で隙間最小化
6. **未配置タスク**: `status="unplaced"` → UI で赤表示 + Toast

```python
def quantize(dt: datetime, *, up: bool) -> datetime:
    """10 分単位で丸める"""
    q = 600  # 秒
    ts = dt.timestamp()
    rounded = (math.ceil(ts / q) if up else math.floor(ts / q)) * q
    return datetime.utcfromtimestamp(rounded)
```

---

# 8. UI / UX

* Tailwind CSS v3 + Alpine.js v3 + HTML5
* sticky header / CSS Grid 時間軸 / サイドパネル Tasks
* DnD: `.dragging{opacity:.5}`, drop target `.ring-2 ring-blue-400`
* Undo/Redo (Command Pattern) 履歴 20
* 印刷: `@media print` で操作 UI 非表示、A4 portrait margin 10 mm、表紙に QR

---

# 9. 時刻 & タイムゾーン

| 項目    | 内容                                                           |
| ----- | ------------------------------------------------------------ |
| 内部    | UTC (RFC 3339) 固定                                            |
| 表示    | JST (Asia/Tokyo) — `luxon` (front) / `pytz` (back)           |
| TZ 検証 | Google イベントの `event.timeZone` が IANA TZDB 2025‑b 以外 → UTC 扱い |
| DST   | `pytz` 変換で ±1 h ずれ防止                                         |

---

# 10. OAuth2 PKCE

| 項目             | 値                                                   |
| -------------- | --------------------------------------------------- |
| Flow           | OAuth 2.1 authorization\_code + PKCE (S256)         |
| code\_verifier | 128 byte URL‑safe Base64                            |
| Token 保存       | `sessionStorage` AES‑GCM 256（ブラウザ再起動で失効）            |
| Scope          | `openid profile email` + Calendar & Sheets readonly |
| Refresh        | silent refresh (iframe + `prompt=none`)             |

---

# 11. セキュリティ

* **XSS**: Jinja2 `{{ v \| e }}` / `textContent` / Trusted Types
* **CSRF**: SameSite=Lax + double‑submit token
* **CSP**: `default-src 'self'; connect-src 'self' https://www.googleapis.com`
* **Rate‑Limit**: Cloud Armor 60 req/min/IP
* **依存監査**: `pip-audit`, `npm audit` を CI 強制

---

# 12. テスト戦略

| レイヤ         | ツール                | 目的                     |
| ----------- | ------------------ | ---------------------- |
| Unit        | pytest + freezegun | 丸め・TZ 変換               |
| Integration | pytest + httpretty | Google API モック         |
| E2E         | Playwright         | UI / DnD / PWA offline |
| Security    | dlint, OWASP ZAP   | XSS / CSRF             |

---

# 13. CI / CD（GitHub Actions）

```yaml
name: CI
on:
  push:
    branches: [ main ]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      - run: python -m pip install -r requirements.dev.txt
      - run: ruff check .
      - run: pytest -q

  deploy:
    if: github.ref == 'refs/heads/main'
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/setup-gcloud@v1
        with:
          project_id: ${{ secrets.GCP_PROJECT }}
          service_account_key: ${{ secrets.GCP_SA_KEY }}
          export_default_credentials: true
      - run: gcloud builds submit --pack image=gcr.io/$GCP_PROJECT/schedule-app
      - run: |
          gcloud run deploy schedule-app \
            --image gcr.io/$GCP_PROJECT/schedule-app \
            --region asia-northeast1 \
            --platform managed \
            --quiet
```

---

# 14. 運用監視

* **SLO**

  * `request_latency_p95 < 0.4 s`
  * `unplaced_task_rate < 3 %`
* **Alert**

  * ErrorRate > 2 % または latency >SLO → PagerDuty

---

# 15. PWA（Phase 3）

1. **Service Worker** — `network‑first`、失敗時 `Cache‑fallback`
2. **Cache Storage** — 最新スケジュール JSON＋HTML を保存
3. **Web App Manifest**

```json
{
  "name": "1‑Day Schedule",
  "short_name": "Schedule",
  "start_url": "/?source=pwa",
  "display": "standalone",
  "theme_color": "#2563EB",
  "background_color": "#FFFFFF",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" }
  ]
}
```

---

# 16. 国際化（Phase 2）

* `@formatjs/intl-messageformat` v3
* 既定 = 日本語、`Accept-Language: en` なら英語 UI
* 翻訳キーは PascalCase (`Schedule.Generated`)

---

# 17. ディレクトリ構成（最終形）

```
schedule-app/
├─ schedule_app/
│  ├─ __init__.py
│  ├─ config.py
│  ├─ models.py
│  ├─ services/
│  │   ├─ google_client.py
│  │   ├─ schedule.py
│  │   ├─ rounding.py
│  │   └─ metrics.py
│  ├─ api/
│  │   ├─ calendar.py
│  │   ├─ tasks.py
│  │   ├─ blocks.py
│  │   └─ schedule.py
│  └─ templates/
│      ├─ index.html
│      └─ print.html
│  └─ static/
│      ├─ js/
│      │   ├─ app.js
│      │   └─ sw.js
│      └─ css/
│          └─ styles.css
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ e2e/
├─ requirements.txt
├─ requirements.dev.txt
├─ .pre-commit-config.yaml
├─ .ruff.toml
└─ .vscode/
    ├─ settings.json
    ├─ launch.json
    └─ tasks.json
```

---

# 18. エージェント操作チートシート

| 操作      | VS Code コマンド                  | 備考                          |
| ------- | ----------------------------- | --------------------------- |
| ファイル生成  | **Codex: Create New File**    | パスと内容を入力                    |
| 既存編集    | **Codex: Edit File**          | 差分を自然言語で指示                  |
| テスト実行   | **Run Tests** タスク or `pytest` | 失敗行をハイライト                   |
| Lint 修正 | 保存時 Ruff 自動適用                 | `editor.formatOnSave: true` |

---

# 19. FAQ

| Q             | A                                         |
| ------------- | ----------------------------------------- |
| Docker で動かせる？ | 可能だが **非推奨**。CI/CD は Buildpacks で自動コンテナ化。 |
| VS Code 必須？   | 他 IDE でも動くがガイド外。                          |
| macOS でも？     | `python3 -m venv .venv` で同様。パスを適宜変更。      |

---

# 20. まとめ — 5 ステップで完成

1. **clone → `.venv` 作成 → 依存インストール**
2. **`flask run` でローカル起動 → Google OAuth 通過**
3. **VS Code でファイルを “Codex: Create/Edit”**
4. **`pytest` + Playwright で緑を確認**
5. **`git push` → GitHub Actions が自動で Cloud Run へデプロイ**

---


