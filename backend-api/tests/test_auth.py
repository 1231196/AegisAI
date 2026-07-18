"""Tests for the auth endpoints (login, refresh, logout, /me)."""

from __future__ import annotations

import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app.auth.repositories import RefreshTokenRepository
from app.auth.security import decode_access_token
from app.config import settings
from app.main import app

client = TestClient(app)


def _login(username: str = "demo", password: str = "testpassword") -> dict:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()


# ---------------------------------------------------------------------------
# US-003 backward-compatibility: login response + JWT shape
# ---------------------------------------------------------------------------


def test_login_with_valid_credentials_returns_signed_jwt():
    body = _login()

    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and body["access_token"]
    assert body["expires_in"] == settings.jwt_expire_minutes * 60

    payload = jwt.decode(
        body["access_token"],
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    assert payload["sub"] == "demo"
    assert payload["type"] == "access"
    assert "uid" in payload
    assert "role" in payload
    assert "org" in payload
    assert "iat" in payload
    assert "exp" in payload
    assert payload["exp"] > payload["iat"]


def test_login_with_wrong_password_returns_401():
    response = client.post(
        "/auth/login",
        json={"username": "demo", "password": "definitely-wrong"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


def test_login_with_unknown_user_returns_401():
    response = client.post(
        "/auth/login",
        json={"username": "ghost-user", "password": "anything"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


def test_login_error_response_is_identical_for_unknown_user_and_wrong_password():
    wrong_pw = client.post(
        "/auth/login",
        json={"username": "demo", "password": "nope"},
    ).json()
    unknown = client.post(
        "/auth/login",
        json={"username": "nope", "password": "nope"},
    ).json()
    assert wrong_pw == unknown


def test_login_strips_whitespace_from_username():
    response = client.post(
        "/auth/login",
        json={"username": "  demo  ", "password": "testpassword"},
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_decode_rejects_token_signed_with_wrong_secret():
    forged = jwt.encode(
        {"sub": "demo", "type": "access", "exp": 9999999999},
        "not-the-real-secret",
        algorithm=settings.jwt_algorithm,
    )
    assert decode_access_token(forged) is None


def test_decode_rejects_expired_token():
    now = int(time.time())
    expired = jwt.encode(
        {"sub": "demo", "type": "access", "iat": now - 7200, "exp": now - 3600},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    assert decode_access_token(expired) is None


def test_me_rejects_token_without_subject_claim():
    forged = jwt.encode(
        {"type": "access", "exp": 9999999999},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {forged}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_login_with_whitespace_only_username_returns_422():
    response = client.post(
        "/auth/login",
        json={"username": "   ", "password": "testpassword"},
    )
    assert response.status_code == 422


def test_me_returns_full_user_record():
    """GET /auth/me now returns the full UserOut record, not just username."""
    token = _login()["access_token"]
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "demo"
    assert body["role"] == "admin"
    assert body["organization_id"] == "00000000-0000-0000-0000-000000000001"
    assert body["disabled"] is False
    # No password hash leaked.
    assert "password_hash" not in body


def test_me_rejects_request_without_authorization_header():
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert "Authorization" in response.json()["detail"]


def test_me_rejects_request_with_garbage_token():
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_me_rejects_request_with_non_bearer_scheme():
    token = _login()["access_token"]
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Basic {token}"},
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"username": "demo"},
        {"password": "testpassword"},
        {"username": "", "password": "testpassword"},
        {"username": "demo", "password": ""},
        {"username": "   ", "password": "testpassword"},
    ],
)
def test_login_with_invalid_body_returns_422(body):
    response = client.post("/auth/login", json=body)
    assert response.status_code == 422


def test_login_with_password_only_whitespace_returns_422():
    response = client.post(
        "/auth/login",
        json={"username": "demo", "password": "   "},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# US-004: refresh-token rotation, family-wide revocation on reuse, logout
# ---------------------------------------------------------------------------


def test_login_also_returns_refresh_token():
    body = _login()
    assert isinstance(body["refresh_token"], str) and body["refresh_token"]
    payload = jwt.decode(
        body["refresh_token"],
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    assert payload["type"] == "refresh"
    assert payload["sub"] == "demo"
    assert "jti" in payload


def test_refresh_returns_new_token_pair_and_rotates():
    initial = _login()
    refresh = initial["refresh_token"]

    response = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert response.status_code == 200
    new = response.json()

    assert new["access_token"] != initial["access_token"]
    assert new["refresh_token"] != refresh
    # Both tokens verify.
    assert decode_access_token(new["access_token"]) is not None


def test_refresh_marks_old_token_as_revoked():
    initial = _login()
    old_jti = jwt.decode(
        initial["refresh_token"],
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )["jti"]
    client.post("/auth/refresh", json={"refresh_token": initial["refresh_token"]})
    assert RefreshTokenRepository.is_revoked(old_jti) is True


def test_refresh_rejects_garbage_token():
    response = client.post("/auth/refresh", json={"refresh_token": "not-a-jwt"})
    assert response.status_code == 401


def test_refresh_rejects_reuse_of_rotated_token_and_revokes_family():
    """Token theft signal: presenting a refresh that's already been rotated
    must revoke every active refresh belonging to the same user."""
    initial = _login()
    # First refresh consumes the original
    first = client.post(
        "/auth/refresh",
        json={"refresh_token": initial["refresh_token"]},
    ).json()
    # Second refresh: try to use the original again
    second = client.post(
        "/auth/refresh",
        json={"refresh_token": initial["refresh_token"]},
    )
    assert second.status_code == 401
    assert second.json()["detail"] == "Refresh token revoked"
    # The legitimate replacement should ALSO have been revoked as part
    # of the family-wide sweep.
    third = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )
    assert third.status_code == 401


def test_refresh_rejects_expired_token_before_db_check():
    now = int(time.time())
    expired = jwt.encode(
        {
            "sub": "demo",
            "uid": "00000000-0000-0000-0000-0000000000aa",
            "jti": "stale-jti",
            "type": "refresh",
            "iat": now - 7200,
            "exp": now - 3600,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    response = client.post("/auth/refresh", json={"refresh_token": expired})
    assert response.status_code == 401


def test_refresh_rejects_token_signed_with_wrong_secret():
    forged = jwt.encode(
        {
            "sub": "demo",
            "uid": "00000000-0000-0000-0000-0000000000aa",
            "jti": "forged-jti",
            "type": "refresh",
            "exp": 9999999999,
        },
        "not-the-real-secret",
        algorithm=settings.jwt_algorithm,
    )
    response = client.post("/auth/refresh", json={"refresh_token": forged})
    assert response.status_code == 401


def test_logout_revokes_refresh_token():
    pair = _login()
    refresh_jti = jwt.decode(
        pair["refresh_token"],
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )["jti"]

    response = client.post(
        "/auth/logout",
        json={"refresh_token": pair["refresh_token"]},
        headers={"Authorization": f"Bearer {pair['access_token']}"},
    )
    assert response.status_code == 204
    assert RefreshTokenRepository.is_revoked(refresh_jti) is True

    # Presenting the revoked refresh after logout must be rejected.
    follow_up = client.post(
        "/auth/refresh",
        json={"refresh_token": pair["refresh_token"]},
    )
    assert follow_up.status_code == 401


def test_logout_requires_access_token():
    pair = _login()
    response = client.post(
        "/auth/logout",
        json={"refresh_token": pair["refresh_token"]},
    )  # no Authorization header
    assert response.status_code == 401


def test_logout_is_idempotent_for_unknown_refresh_token():
    pair = _login()
    response = client.post(
        "/auth/logout",
        json={"refresh_token": "definitely-not-issued-by-us"},
        headers={"Authorization": f"Bearer {pair['access_token']}"},
    )
    assert response.status_code == 204  # no info leak


def test_access_token_works_even_after_logout():
    """Per US-004 plan: we revoke refresh but let access expire naturally.
    Logout must NOT blanket-invalidate access tokens immediately."""
    pair = _login()
    client.post(
        "/auth/logout",
        json={"refresh_token": pair["refresh_token"]},
        headers={"Authorization": f"Bearer {pair['access_token']}"},
    )
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {pair['access_token']}"},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Self-service registration (POST /auth/register) — used by the frontend
# ---------------------------------------------------------------------------


def test_register_with_new_email_returns_token_pair():
    response = client.post(
        "/auth/register",
        json={"email": "newuser@example.com", "password": "strongpass1"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and body["access_token"]
    assert isinstance(body["refresh_token"], str) and body["refresh_token"]


def test_register_then_login_works_for_same_credentials():
    client.post(
        "/auth/register",
        json={"email": "second@example.com", "password": "strongpass1"},
    )
    response = client.post(
        "/auth/login",
        json={"username": "second@example.com", "password": "strongpass1"},
    )
    assert response.status_code == 200


def test_register_rejects_duplicate_email_returns_409():
    payload = {"email": "unique@example.com", "password": "strongpass1"}
    first = client.post("/auth/register", json=payload)
    assert first.status_code == 201
    second = client.post("/auth/register", json=payload)
    assert second.status_code == 409
    assert "exists" in second.json()["detail"].lower()


def test_register_rejects_invalid_email_shape_returns_422():
    response = client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "strongpass1"},
    )
    assert response.status_code == 422


def test_register_rejects_short_password_returns_422():
    response = client.post(
        "/auth/register",
        json={"email": "ok@example.com", "password": "short"},
    )
    assert response.status_code == 422


def test_register_normalises_email_and_uses_lowercase():
    response = client.post(
        "/auth/register",
        json={"email": "  MIXED@Example.COM  ", "password": "strongpass1"},
    )
    assert response.status_code == 201
    # Verify the user was actually stored normalised.
    login = client.post(
        "/auth/login",
        json={"username": "mixed@example.com", "password": "strongpass1"},
    )
    assert login.status_code == 200
