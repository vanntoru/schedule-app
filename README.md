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

Execute the unit tests with:

```bash
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
