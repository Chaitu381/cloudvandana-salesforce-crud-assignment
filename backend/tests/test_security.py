import pytest

from app.core.security import (
    SalesforceSession,
    decode_cursor,
    decode_session,
    encode_cursor,
    encode_session,
    new_oauth_transaction,
    parse_oauth_transaction,
)


def test_session_round_trip(settings):
    session = SalesforceSession("access", "refresh", "https://example.my.salesforce.com")
    token = encode_session(settings, session)
    decoded = decode_session(settings, token)
    assert decoded is not None
    assert decoded.access_token == "access"
    assert "access" not in token


def test_oauth_transaction_contains_pkce(settings):
    state, challenge, cookie = new_oauth_transaction(settings)
    tx = parse_oauth_transaction(settings, cookie)
    assert tx["state"] == state
    assert len(challenge) >= 43
    assert tx["verifier"]


def test_cursor_round_trip(settings):
    token = encode_cursor(settings, {"object": "Account", "id": "001000000000000AAA"})
    payload = decode_cursor(settings, token)
    assert payload["object"] == "Account"


def test_invalid_cursor_rejected(settings):
    with pytest.raises(Exception):
        decode_cursor(settings, "invalid")
