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
pip install -r requirements.dev.txt
pre-commit install
flask --app schedule_app run --debug --port 5173
```

## Running Tests

Execute the unit tests with:

```bash
pytest -q
```

