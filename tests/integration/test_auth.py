import re
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse, parse_qs


def test_login_redirect(client):
    """/login は Google 認可 URL へリダイレクトする"""
    resp = client.get("/login")
    assert resp.status_code == 302
    url = resp.headers["Location"]
    assert "accounts.google.com" in url
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    # code_challenge, state, client_id を含むこと
    assert "code_challenge" in qs and qs["code_challenge_method"] == ["S256"]


@patch("schedule_app.__init__.Flow")
def test_callback_exchange(mock_flow, client, app):
    """/callback はトークン交換後 index へリダイレクトする"""
    # ダミーフロー: fetch_token→None, credentials→MagicMock(to_json)
    dummy_creds = MagicMock(to_json=lambda: '{"token":"ya29..."}')
    mock_instance = MagicMock(
        fetch_token=lambda code: None,
        credentials=dummy_creds,
    )
    mock_flow.from_client_config.return_value = mock_instance
    with client.session_transaction() as sess:
        sess["pkce_state"] = "abc123"
    resp = client.get("/callback?state=abc123&code=authcode")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")
    with client.session_transaction() as sess:
        assert "google_creds" in sess
