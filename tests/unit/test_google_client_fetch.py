import pytest
from urllib.error import HTTPError


@pytest.mark.parametrize("status", [401, 403])
def test_fetch_unauthorized(monkeypatch, status):
    from schedule_app.services.google_client import GoogleClient, GoogleAPIUnauthorized

    client = GoogleClient(credentials={"access_token": "tok"})

    def raise_error(req):  # pragma: no cover - stub
        raise HTTPError(req.full_url, status, "", {}, None)

    monkeypatch.setattr("schedule_app.services.google_client.request.urlopen", raise_error)

    with pytest.raises(GoogleAPIUnauthorized):
        client.fetch_calendar_events(
            time_min="2025-01-01T00:00:00Z",
            time_max="2025-01-02T00:00:00Z",
        )

