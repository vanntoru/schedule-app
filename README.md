# Schedule App

A Flask-based web application that generates a printable one-day schedule by merging Google Calendar events, user tasks and blocked time slots.

## Prerequisites

- Python 3.11
- Google account for Calendar access

## Development Setup

Follow these commands on Windows with PowerShell:

```powershell
git clone https://github.com/your-org/schedule-app.git
cd schedule-app
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -U pip
pip install -r requirements.dev.txt  # installs dev packages like freezegun
pre-commit install
flask --app schedule_app run --debug --port 5173
```

The `requirements.dev.txt` file includes **freezegun**, which the tests rely on.

## Configuration

The application reads settings from environment variables. `TIMEZONE` defines
the default IANA zone used when parsing API dates that lack timezone
information. It defaults to `cfg.TIMEZONE` but may be changed to any valid zone
identifier.

## OAuth Setup

Create Google OAuth 2.0 credentials and set `GOOGLE_CLIENT_ID`,
`GOOGLE_CLIENT_SECRET` and `OAUTH_REDIRECT_URI` in your environment. For local
development you can create a `.env` file containing:

```env
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-secret
OAUTH_REDIRECT_URI=http://localhost:5173/callback
BLOCKS_SHEET_ID=your-blocks-sheet-id
```

The application requests the following scopes:

```
openid
https://www.googleapis.com/auth/userinfo.profile
https://www.googleapis.com/auth/userinfo.email
https://www.googleapis.com/auth/calendar.readonly
https://www.googleapis.com/auth/spreadsheets.readonly
```

## Environment

Set `SECRET_KEY` to any random string for Flask session security. A default
`dev-secret-key` is used when the variable is unset, which is suitable for
development only.

## Running Tests

The test suite depends on the `freezegun` library to control time. Tests will
not run until it has been installed from `requirements.dev.txt`:

```bash
pip install -r requirements.dev.txt
pytest -q
```


## Tasks API

Simple in-memory endpoints used by the front-end.

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET | `/api/tasks` | List all tasks |
| POST | `/api/tasks` | Create a task |
| PUT | `/api/tasks/<id>` | Update a task |
| DELETE | `/api/tasks/<id>` | Remove a task |
| GET | `/api/tasks/import` | Fetch tasks from Google Sheets |
| POST | `/api/tasks/import` | Replace tasks with sheet data |
| DELETE | `/api/tasks/cache` | Invalidate Google Sheets tasks cache |

All datetimes are UTC RFC 3339 strings. Validation errors return a 422 response with type `https://schedule.app/errors/invalid-field`. The import endpoints may also return 422 for invalid sheet rows or 502 when Google Sheets cannot be reached.

## Schedule API

| Method | Path | Description |
| ------ | ---- | ----------- |
| POST | `/api/schedule/generate` | Generate a schedule grid for one day |

`date` is a required query parameter that accepts an ISO‑8601 datetime
(e.g. `2025-01-01T09:00:00+09:00`) or `YYYY-MM-DD`. When the value lacks a
timezone, it is interpreted using `cfg.TIMEZONE` (JST). The endpoint forwards
this JST date to the service layer, which converts it to UTC.
<!-- TODO: support selecting different scheduling algorithms -->
On success, the endpoint returns `200 OK` with a JSON object:


```json
{
  "date": "2025-01-01",
  "slots": [0, 1, 2, ...],
  "unplaced": []
}
```

`slots` is an array of 144 ten-minute entries where `0` means free, `1` busy and
`2` occupied by a task. Missing or malformed query parameters yield
`400 Bad Request`. Invalid task, event or block data returns a `422` problem
response.


## Calendar API

`GET /api/calendar` returns Google events for the given day. If credentials are
missing, expired or revoked, the endpoint responds with **401 Unauthorized** and
provides instructions in the JSON body to re-authenticate via `/login`.
The required `date` query parameter accepts an ISO 8601 datetime or
`YYYY-MM-DD`. When no timezone is included, the value is interpreted using
`cfg.TIMEZONE` and normalized to UTC before calling the
Google API.

The front-end will automatically build the `#time-grid` element at page load if
it is missing.

終日イベントはページ上部にチップ形式で表示され、スケジュールには配置されません。

Google API スタブは終日イベントだけでなく時間指定イベントも返します。


## Google Calendar Stub

```python
from schedule_app.services.google_client import GoogleClient

app.extensions["gclient"] = GoogleClient(credentials=None)
```

