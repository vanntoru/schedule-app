import os
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from schedule_app import create_app


@pytest.fixture
def app():
    os.environ.setdefault("GOOGLE_CLIENT_ID", "dummy-client-id")
    os.environ.setdefault("GOOGLE_CLIENT_SECRET", "dummy-secret")
    os.environ.setdefault("GOOGLE_REDIRECT_URI", "http://localhost:5173/callback")
    app = create_app()
    app.testing = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()
