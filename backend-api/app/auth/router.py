"""Auth router: /login, /refresh, /logout, /me."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_bearer_token, get_current_user
from app.auth.repositories import (
    OrganizationRepository,
    RefreshTokenRepository,
    UserRepository,
)
from app.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    PermissionsResponse,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserOut,
)
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.auth.users import UNREACHABLE_HASH
from app.auth.permissions import permissions_for_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_token_pair(user: dict) -> tuple[TokenPair, str]:
    """Mint a fresh access+refresh pair for ``user``.

    Returns the ``TokenPair`` for the caller to ship, plus the new
    refresh jti so the caller can record the rotation in the same
    request without round-trip-decoding the just-minted token.
    """
    access = create_access_token(
        user_id=user["id"],
        username=user["username"],
        role=user["role"],
        organization_id=user["organization_id"],
    )
    refresh = create_refresh_token(
        user_id=user["id"],
        username=user["username"],
    )
    pair = TokenPair(
        access_token=access.token,
        refresh_token=refresh.token,
        token_type="bearer",
        expires_in=access.expires_in,
    )
    return pair, refresh.jti


@router.post("/login", response_model=TokenPair)
def login(credentials: LoginRequest) -> TokenPair:
    """Authenticate a user and return a fresh access+refresh pair.

    Returns 401 with the same error message for both unknown usernames
    and wrong passwords to avoid leaking which usernames exist. Bcrypt
    is always run (even for unknown users) so response time stays
    roughly constant regardless of whether the submitted username is
    valid.

    Side-effect: every successful /auth/login *sweeps* any pre-existing
    refresh tokens for the same user. Without this, repeated
    login/logout cycles keep appending one jti per login to
    ``RefreshTokenRepository._by_jti`` (logout only revokes the
    specific jti the caller hands in), so the family grows unbounded
    in long-running dev sessions. The accumulated siblings then race
    on the next /auth/refresh: any stale request whose jti got
    superseded produces "Refresh rotation conflict: family sweep
    revoked N sibling(s)" + a 401 in the browser console even though
    every request was a legitimate login for the same user. Holding
    only the latest refresh is also defence-in-depth — a leaked
    prior refresh stops working the moment that user re-authenticates.
    """
    user = UserRepository.get_by_username(credentials.username)
    hash_to_check = user["password_hash"] if user is not None else UNREACHABLE_HASH
    password_valid = verify_password(credentials.password, hash_to_check)

    if user is None or not password_valid or user.get("disabled"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    RefreshTokenRepository.revoke_all_for_user(user["id"])
    pair, _jti = _issue_token_pair(user)
    return pair


_DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000999"


def _ensure_default_org() -> dict:
    """Return the default organisation, creating it on first signup.

    Self-service registration needs *some* organisation to anchor the
    new user to. In production this bootstrap step would be replaced
    by an invite-token / tenant-onboarding flow.
    """
    existing = OrganizationRepository.get_by_slug("default")
    if existing is not None:
        return existing
    return OrganizationRepository.seed(
        id_=_DEFAULT_ORG_ID,
        name="Default",
        slug="default",
    )


@router.post(
    "/register",
    response_model=TokenPair,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterRequest) -> TokenPair:
    """Self-service signup. Creates a ``customer`` user in the default
    organisation and returns the same TokenPair shape as ``/auth/login``.
    """
    if UserRepository.username_exists(payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists",
        )
    org = _ensure_default_org()
    user = UserRepository.create(
        username=payload.email,
        password_hash=hash_password(payload.password),
        role="customer",
        organization_id=org["id"],
    )
    pair, _jti = _issue_token_pair(user)
    logger.info(
        "Registered new user %s in org %s",
        user["username"],
        user["organization_id"],
    )
    return pair


@router.post("/refresh", response_model=TokenPair)
def refresh(request: RefreshRequest) -> TokenPair:
    """Trade a valid refresh token for a new access+refresh pair.

    Implements atomic rotation via ``claim_for_rotation``: if another
    concurrent request has already claimed this refresh (the classic
    rotation race), this call loses — the new pair is destroyed by a
    family-wide sweep and 401 is returned.
    """
    payload = decode_refresh_token(request.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    jti = payload.get("jti")
    uid = payload.get("uid")
    username = payload.get("sub")
    if (
        not isinstance(jti, str)
        or not isinstance(uid, str)
        or not isinstance(username, str)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    record = RefreshTokenRepository.get(jti)
    if record is None:
        # Signed correctly but never issued by us — treat as invalid.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    user = UserRepository.get_by_id(uid)
    if user is None or user.get("disabled"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
        )
    # Mint the new pair *before* claiming, so the new jti is available.
    new_pair, new_jti = _issue_token_pair(user)
    # Atomically swap the old refresh for the new one. Concurrent /refresh
    # calls on the same jti now serialise — losers see ``rejected_at``
    # already set and lose the family.
    if not RefreshTokenRepository.claim_for_rotation(jti, new_jti):
        revoked = RefreshTokenRepository.revoke_all_for_user(uid)
        logger.warning(
            "Refresh rotation conflict: jti=%s user=%s; family sweep revoked %d sibling(s)",
            jti,
            uid,
            revoked,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked",
        )
    return new_pair


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: LogoutRequest,
    _token: str = Depends(get_bearer_token),
) -> None:
    """Revoke the named refresh token. Idempotent on unknown jtis."""
    refresh_payload = decode_refresh_token(payload.refresh_token)
    if refresh_payload is None:
        # Don't leak which refresh tokens are issued — just 204. We do
        # log here though: an unparseable refresh at /logout is a
        # suspicious signal worth tracking in SIEM, since legitimate
        # callers always send a server-issued token.
        logger.warning(
            "/auth/logout received an unparseable refresh token; nothing to revoke",
        )
        return None
    jti = refresh_payload.get("jti")
    if not isinstance(jti, str):
        # Token parses + signature checks out, but lacked ``jti``. Treated
        # as a probe signal — without the claim we cannot identify the
        # row to revoke, so we surface this in logs for SIEM ingest.
        logger.warning(
            "/auth/logout refresh payload lacks a jti claim; nothing to revoke",
        )
        return None
    RefreshTokenRepository.revoke(jti)
    return None


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Return the caller's user record.

    The access JWT is verified and the user is loaded fresh from the
    repository on every call, so revocation/role changes propagate
    within the access-token's lifetime without a refresh.
    """
    return current_user


@router.get("/me/permissions", response_model=PermissionsResponse)
def read_current_user_permissions(
    current_user: dict = Depends(get_current_user),
) -> PermissionsResponse:
    """Return the caller's role + permission set derived from the catalog.

    The SPA fetches this on hydration so role-aware UI rendering does
    not have to hardcode the catalog. The endpoint is auth-required
    (`get_current_user`) but does not constrain by role — every
    authenticated user can introspect their own permission set.
    """
    role = current_user.get("role", "")
    return PermissionsResponse(
        role=role,
        permissions=sorted(permissions_for_role(role)),
    )
