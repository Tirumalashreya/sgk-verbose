"""Fixed username/password access, not a public signup flow — the app is
meant for a small, known group (shared by Tailscale invite, not an app
store listing), so there's no account system to build: just a short list
of credentials you create yourself in .env, checked on every request.

APP_USERS in .env: "user1:pass1,user2:pass2" — comma-separated pairs. If
it's empty, auth is off entirely (local dev, matches how this ran before
today — never disable it once this is reachable by anyone but you)."""
import base64
import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

_security = HTTPBasic(auto_error=False)


def _users() -> dict[str, str]:
    raw = os.getenv("APP_USERS", "")
    users = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        user, _, pw = pair.partition(":")
        users[user] = pw
    return users


def auth_enabled() -> bool:
    return bool(_users())


def _check(username: str, password: str) -> bool:
    users = _users()
    expected = users.get(username)
    # A plain `==` leaks timing information about how many leading
    # characters matched — compare_digest takes the same time regardless,
    # so a wrong guess can't be narrowed down one character at a time.
    # Still check against *some* password when the username is unknown
    # (a dummy value), so the response doesn't come back faster for a
    # username that doesn't exist at all — that timing gap is itself a
    # way to enumerate valid usernames.
    return secrets.compare_digest(password, expected or "\0no-such-user\0")


def verify_credentials(credentials: HTTPBasicCredentials = Depends(_security)) -> str:
    """A FastAPI dependency — add once at the app level and it guards every
    REST route automatically, without touching each endpoint."""
    if not auth_enabled():
        return "dev"
    if credentials is None or not _check(credentials.username, credentials.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials",
                            headers={"WWW-Authenticate": "Basic"})
    return credentials.username


def username_from_header(header: str | None) -> str | None:
    """The username behind a Basic Auth header, once the password's been
    verified against it — None for a missing/malformed header or a wrong
    password. Used to attribute an action (a session, an error) to whoever
    was actually logged in, not to gate anything itself."""
    if not header or not header.startswith("Basic "):
        return None
    try:
        decoded = base64.b64decode(header[len("Basic "):]).decode("utf-8")
        username, _, password = decoded.partition(":")
    except Exception:
        return None
    return username if _check(username, password) else None


def check_basic_header(header: str | None) -> bool:
    """Same check as verify_credentials, but against a raw Authorization
    header string — used by the HTTP-only auth middleware (api.py), since
    FastAPI's HTTPBasic security class isn't WebSocket-safe when wired up
    as an app-level dependency (it crashes on a websocket scope), so plain
    HTTP routes are now guarded by middleware instead."""
    if not auth_enabled():
        return True
    return username_from_header(header) is not None


def _admin_check(username: str, password: str) -> bool:
    expected_user = os.getenv("ADMIN_USER", "")
    expected_pw = os.getenv("ADMIN_PASSWORD", "")
    if not expected_user or not expected_pw:
        return False
    return secrets.compare_digest(username, expected_user) and secrets.compare_digest(password, expected_pw)


def check_admin_header(header: str | None) -> bool:
    """Separate credentials from APP_USERS — the owner-only /admin page isn't
    reachable with any of the 10 regular app logins, only ADMIN_USER/PASSWORD."""
    if not header or not header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(header[len("Basic "):]).decode("utf-8")
        username, _, password = decoded.partition(":")
    except Exception:
        return False
    return _admin_check(username, password)


def verify_ws_token(token: str | None) -> bool:
    """The WebSocket handshake can't carry a Basic Auth header the way a
    fetch() call can — a browser/RN WebSocket client has no API for custom
    headers on the opening request. The same username:password the app
    already has (from its Basic Auth login) gets base64-encoded into a
    query parameter instead; this decodes and checks it the same way."""
    if not auth_enabled():
        return True
    if not token:
        return False
    try:
        decoded = base64.b64decode(token).decode("utf-8")
        username, _, password = decoded.partition(":")
    except Exception:
        return False
    return _check(username, password)
