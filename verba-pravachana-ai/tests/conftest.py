"""Tests must never depend on the real .env's APP_USERS — otherwise adding
real credentials there (for the actual running app) silently makes every
TestClient call in the suite start returning 401, since auth.py reads the
environment fresh on every request, not a value cached at import time."""
import pytest


@pytest.fixture(autouse=True)
def _no_auth_in_tests(monkeypatch):
    monkeypatch.delenv("APP_USERS", raising=False)
