"""GoogleClient が import だけで失敗しないことを確認する最小テスト."""

def test_google_client_import():
    from schedule_app.services.google_client import GoogleClient, SCOPES  # noqa: F401

    # スコープが仕様どおりリスト型
    assert isinstance(SCOPES, (list, tuple))
