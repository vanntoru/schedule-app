from schedule_app import create_app


def test_create_app_has_google_client_extension():
    from schedule_app.services.google_client import GoogleClient
    app = create_app(testing=True)
    assert "gclient" in app.extensions
    assert isinstance(app.extensions["gclient"], GoogleClient)
