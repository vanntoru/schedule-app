import schedule_app


def test_build_flow_scopes(monkeypatch):
    captured = {}

    def dummy_get_setting(name: str) -> str:
        return "dummy"

    def dummy_from_client_config(client_config, scopes, redirect_uri=None):
        captured["scopes"] = scopes
        class DummyFlow:
            pass
        return DummyFlow()

    monkeypatch.setattr("schedule_app._get_setting", dummy_get_setting)
    monkeypatch.setattr("schedule_app.Flow.from_client_config", dummy_from_client_config)

    schedule_app._build_flow(redirect_uri="http://localhost")
    assert "https://www.googleapis.com/auth/spreadsheets.readonly" in captured["scopes"]

