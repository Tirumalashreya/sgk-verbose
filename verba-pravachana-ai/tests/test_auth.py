"""Fixed username/password, not a signup flow — a short list in APP_USERS,
checked on every REST request (app-level dependency) and on the WebSocket
handshake (its own check, since FastAPI's app-level dependencies don't
reach WebSocket routes). Empty APP_USERS means auth is off — that's today's
default (local dev), never the state once this is reachable by anyone else."""
import base64
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
import pytest


def test_auth_disabled_when_app_users_is_empty(monkeypatch):
    import auth
    monkeypatch.delenv("APP_USERS", raising=False)
    assert auth.auth_enabled() is False
    # verify_credentials must not raise even with no credentials offered
    assert auth.verify_credentials(None) == "dev"


def test_auth_enabled_once_app_users_is_set(monkeypatch):
    import auth
    monkeypatch.setenv("APP_USERS", "shreya:secret123")
    assert auth.auth_enabled() is True


def test_correct_credentials_are_accepted(monkeypatch):
    import auth
    monkeypatch.setenv("APP_USERS", "shreya:secret123,amma:otherpass")
    creds = HTTPBasicCredentials(username="shreya", password="secret123")
    assert auth.verify_credentials(creds) == "shreya"
    creds2 = HTTPBasicCredentials(username="amma", password="otherpass")
    assert auth.verify_credentials(creds2) == "amma"


def test_wrong_password_is_rejected(monkeypatch):
    import auth
    monkeypatch.setenv("APP_USERS", "shreya:secret123")
    creds = HTTPBasicCredentials(username="shreya", password="wrong")
    with pytest.raises(HTTPException) as exc:
        auth.verify_credentials(creds)
    assert exc.value.status_code == 401


def test_unknown_username_is_rejected(monkeypatch):
    import auth
    monkeypatch.setenv("APP_USERS", "shreya:secret123")
    creds = HTTPBasicCredentials(username="nobody", password="secret123")
    with pytest.raises(HTTPException) as exc:
        auth.verify_credentials(creds)
    assert exc.value.status_code == 401


def test_no_credentials_offered_is_rejected_once_auth_is_on(monkeypatch):
    import auth
    monkeypatch.setenv("APP_USERS", "shreya:secret123")
    with pytest.raises(HTTPException) as exc:
        auth.verify_credentials(None)
    assert exc.value.status_code == 401


def test_websocket_token_accepts_correct_base64_credentials(monkeypatch):
    import auth
    monkeypatch.setenv("APP_USERS", "shreya:secret123")
    token = base64.b64encode(b"shreya:secret123").decode()
    assert auth.verify_ws_token(token) is True


def test_websocket_token_rejects_wrong_credentials(monkeypatch):
    import auth
    monkeypatch.setenv("APP_USERS", "shreya:secret123")
    token = base64.b64encode(b"shreya:wrongpass").decode()
    assert auth.verify_ws_token(token) is False


def test_websocket_token_rejects_missing_or_garbage_token(monkeypatch):
    import auth
    monkeypatch.setenv("APP_USERS", "shreya:secret123")
    assert auth.verify_ws_token(None) is False
    assert auth.verify_ws_token("not-valid-base64!!!") is False


def test_websocket_token_passes_through_when_auth_disabled(monkeypatch):
    import auth
    monkeypatch.delenv("APP_USERS", raising=False)
    assert auth.verify_ws_token(None) is True
    assert auth.verify_ws_token("anything") is True


def test_app_users_parses_multiple_pairs_and_ignores_blanks(monkeypatch):
    import auth
    monkeypatch.setenv("APP_USERS", "shreya:pass1, amma:pass2 ,,")
    users = auth._users()
    assert users == {"shreya": "pass1", "amma": "pass2"}
