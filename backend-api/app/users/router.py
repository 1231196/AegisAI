"""User CRUD router (US-005) with RBAC and org isolation (US-006, US-007).

Permission model
----------------
Two scopes:

* ``admin`` — tenant-scoped. Can manage users only inside their own
  organisation. The original US-007 contract is preserved verbatim.
* ``platform_admin`` — cross-tenant. Can see and manage every
  organisation and every user. The router delegates the "is this
  caller cross-tenant?" decision to ``app.auth.schemas.is_cross_tenant``
  so the security contract is auditable in one place.

Both scopes still go through ``require_role(["admin", "platform_admin"])``;
the cross-tenant logic inside the handler is a separate branch.

Org transfer safety
-------------------
PATCHing ``organization_id`` moves the user to another organisation.
Because the user's access JWT bakes ``organization_id`` into its
payload, the router MUST revoke their refresh tokens so the next
``/auth/refresh`` re-mints a pair reflecting the new org. (The current
access token expires within ``jwt_expire_minutes`` and the backend
re-reads the user row for every tenant check, so no security boundary
is crossed — the revoke just keeps the UI/state consistent faster.)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import require_role
from app.auth.repositories import (
    OrganizationRepository,
    RefreshTokenRepository,
    UserRepository,
)
from app.auth.schemas import UserOut, is_cross_tenant
from app.auth.security import hash_password
from app.users.schemas import UserCreateRequest, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["users"])


def _to_user_out(record: dict) -> UserOut:
    return UserOut(
        id=record["id"],
        username=record["username"],
        role=record["role"],
        disabled=record["disabled"],
        organization_id=record["organization_id"],
    )


@router.get("", response_model=list[UserOut])
def list_users(
    current_user: dict = Depends(require_role(["admin", "platform_admin"])),
    organization_id: str | None = Query(
        default=None,
        description=(
            "Optional filter. Plain ``admin`` may only filter within "
            "their own organisation; ``platform_admin`` may filter by "
            "any id."
        ),
    ),
) -> list[UserOut]:
    """List users.

    * ``platform_admin``: defaults to *all users* across every org.
      Narrow with ``?organization_id=<id>``.
    * ``admin``: tenant-scoped to the caller's org. The optional
      ``organization_id`` filter is ignored if it points outside the
      caller's own org (returns the caller's view anyway), so a plain
      admin cannot enumerate foreign orgs via this endpoint.
    """
    if is_cross_tenant(current_user.get("role")):
        if organization_id is not None:
            records = UserRepository.list_in_organization(organization_id)
        else:
            records = UserRepository.list_all()
        return [_to_user_out(u) for u in records]
    # Tenant-scoped admin.
    return [
        _to_user_out(u)
        for u in UserRepository.list_in_organization(current_user["organization_id"])
    ]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateRequest,
    current_user: dict = Depends(require_role(["admin", "platform_admin"])),
) -> UserOut:
    """Create a user.

    ``platform_admin`` may anchor the new user to any existing
    organisation. ``admin`` must use their own organisation (the
    foreign-org attempt returns 403).
    """
    if UserRepository.username_exists(payload.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )
    # First validate the structural value (does the org exist at all?),
    # then enforce the tenant-scope (US-007). 400 for malformed input,
    # 403 for valid-but-foreign.
    if OrganizationRepository.get_by_id(payload.organization_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown organization_id",
        )
    if not is_cross_tenant(current_user.get("role")):
        if payload.organization_id != current_user["organization_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create users outside of your own organization",
            )
    record = UserRepository.create(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        organization_id=payload.organization_id,
        disabled=payload.disabled,
    )
    return _to_user_out(record)


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: str,
    current_user: dict = Depends(require_role(["admin", "platform_admin"])),
) -> UserOut:
    """Fetch a user.

    ``platform_admin`` may read any user. ``admin`` may only read
    users inside their own org; the foreign-org attempt returns 404
    to avoid leaking whether the user exists.
    """
    record = UserRepository.get_by_id(user_id)
    if record is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not is_cross_tenant(current_user.get("role")):
        if record["organization_id"] != current_user["organization_id"]:
            raise HTTPException(status_code=404, detail="User not found")
    return _to_user_out(record)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    current_user: dict = Depends(require_role(["admin", "platform_admin"])),
) -> UserOut:
    """Partial update.

    Fields: ``password``, ``role``, ``disabled``, ``organization_id``
    (the last is a transfer to another org, see module docstring).
    Tenant-scope applies to ``admin`` for everything *except* the
    read fetch — a tenant admin can't even *find* a foreign user to
    patch them, because the GET returns 404 first.
    """
    record = UserRepository.get_by_id(user_id)
    if record is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not is_cross_tenant(current_user.get("role")):
        if record["organization_id"] != current_user["organization_id"]:
            raise HTTPException(status_code=404, detail="User not found")

    updates: dict = {}
    transfer_to_org: str | None = None
    if payload.password is not None:
        updates["password_hash"] = hash_password(payload.password)
    if payload.role is not None:
        updates["role"] = payload.role
    if payload.disabled is not None:
        updates["disabled"] = payload.disabled
    if payload.organization_id is not None:
        # Validate the target org exists structurally before mutating
        # the row. 400 for unknown id; 403 for cross-tenant admin.
        if OrganizationRepository.get_by_id(payload.organization_id) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unknown organization_id",
            )
        if not is_cross_tenant(current_user.get("role")):
            if payload.organization_id != current_user["organization_id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot move users outside of your own organization",
                )
        # Always include the field in the update so the ``if not
        # updates`` guard below doesn't reject an idempotent
        # transfer (PATCH with target == current is still 200, but
        # not a "no fields" mistake). The SQL UPDATE setting a
        # column to its current value is harmless.
        updates["organization_id"] = payload.organization_id
        # Refresh-revoke only when the value actually CHANGES — a
        # no-op write must not invalidate the user's session.
        if payload.organization_id != record["organization_id"]:
            transfer_to_org = payload.organization_id

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No fields to update. Provide at least one of: "
                "password, role, disabled, organization_id."
            ),
        )

    new_record = UserRepository.update(user_id, **updates)
    assert new_record is not None  # existence already enforced above

    # Org transfer safety: any active refresh tokens held by this user
    # would mint access tokens with the OLD organization_id claim on
    # their next rotation. Force a rotation family sweep now so the
    # next /refresh forces a full re-login and a fresh pair with the
    # new org in the payload.
    if transfer_to_org is not None:
        revoked = RefreshTokenRepository.revoke_all_for_user(user_id)
        # Logged at INFO so operators can correlate transfers in audit
        # trails. Not a security signal at this point — the operator
        # initiated the transfer via this very endpoint.
        import logging
        logging.getLogger(__name__).info(
            "user %s transferred to org %s; revoked %d refresh token(s)",
            user_id,
            transfer_to_org,
            revoked,
        )

    return _to_user_out(new_record)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    current_user: dict = Depends(require_role(["admin", "platform_admin"])),
) -> None:
    """Delete a user. Cannot delete yourself.

    ``platform_admin`` may delete users in any org. ``admin`` may
    delete only inside their own org (foreign attempts return 404
    so existence isn't leaked).
    """
    if user_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )
    record = UserRepository.get_by_id(user_id)
    if record is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not is_cross_tenant(current_user.get("role")):
        if record["organization_id"] != current_user["organization_id"]:
            raise HTTPException(status_code=404, detail="User not found")
    UserRepository.delete(user_id)
    return None
