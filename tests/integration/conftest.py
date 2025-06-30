import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from schedule_app import create_app


@pytest.fixture
def app():
    app = create_app()
    app.config.update(SECRET_KEY="test", TESTING=True)
    return app


@pytest.fixture
def client(app):
    return app.test_client()
