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

## Running Tests

The tests rely on the `freezegun` library to control time. Make sure it is
installed from `requirements.dev.txt` before invoking `pytest`:

```bash
pip install -r requirements.dev.txt  # includes freezegun
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

All datetimes are UTC RFC 3339 strings. Validation errors return a 422 response with type `https://schedule.app/errors/invalid-field`.

## Schedule API

| Method | Path | Description |
| ------ | ---- | ----------- |
| POST | `/api/schedule/generate` | Generate a schedule grid for one day |

`date` is a required query parameter in `YYYY-MM-DD` format.
<!-- TODO: support selecting different scheduling algorithms -->

On success, the endpoint returns `200 OK` with just the `slots` array:

```json
[0, 1, 2, ...]
```

`slots` is an array of 144 ten-minute entries where `0` means free, `1` busy and
`2` occupied by a task. The underlying `schedule.generate_schedule()` service
function still returns a dictionary with `date`, `slots` and `unplaced`
for use in other parts of the application. Missing or malformed query
parameters yield `400 Bad Request`. Invalid task, event or block data returns a
`422` problem response.

## Calendar API

`GET /api/calendar` returns Google events for the given day. If credentials are
missing, expired or revoked, the endpoint responds with **401 Unauthorized** and
provides instructions in the JSON body to re-authenticate via `/login`.

The front-end will automatically build the `#time-grid` element at page load if
it is missing.


## Google Calendar Stub

```python
from schedule_app.services.google_client import GoogleClient

app.extensions["gclient"] = GoogleClient(credentials=None)
```

