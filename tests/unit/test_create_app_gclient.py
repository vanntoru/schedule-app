from schedule_app import create_app
from schedule_app.services.google_client import GoogleClient


def test_create_app_has_google_client_extension():
    app = create_app(testing=True)
    assert "gclient" in app.extensions
    assert isinstance(app.extensions["gclient"], GoogleClient)
