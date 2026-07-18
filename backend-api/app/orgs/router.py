"""Organization router (US-007) with platform_admin cross-tenant scope.

Permission model
----------------
Two scopes:

* ``admin`` — tenant-scoped. Can read/create organisations **only**
  in their own context. Existing list endpoint shows just the
  caller's own organisation (US-007 isolation contract preserved).
* ``platform_admin`` — cross-tenant. Can list every organisation,
  fetch any by id, create new ones, and delete empty organisations.

The DELETE endpoint refuses to drop organisations with active users
to prevent catastrophic accidental data loss. Operators must drain
the org (delete or transfer members) before the row can be removed.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import require_role
from app.auth.repositories import OrganizationRepository
from app.auth.schemas import CROSS_TENANT_ROLES, is_cross_tenant
from app.orgs.schemas import OrganizationCreateRequest, OrganizationOut

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _to_org_out(record: dict) -> OrganizationOut:
    return OrganizationOut(
        id=record["id"],
        name=record["name"],
        slug=record["slug"],
    )


@router.get("", response_model=list[OrganizationOut])
def list_organizations(
    current_user: dict = Depends(require_role(["admin", "platform_admin"])),
) -> list[OrganizationOut]:
    """List organisations.

    * ``platform_admin``: every org (used by the admin Organisations
      page so the operator can pick a target when creating a user).
    * ``admin``: only their own org. US-007 isolation contract
      preserved.
    """
    if is_cross_tenant(current_user.get("role")):
        return [_to_org_out(o) for o in OrganizationRepository.list_all()]
    record = OrganizationRepository.get_by_id(current_user["organization_id"])
    if record is None:
        # Caller's user record references an org that no longer exists.
        return []
    return [_to_org_out(record)]


@router.get("/{org_id}", response_model=OrganizationOut)
def get_organization(
    org_id: str,
    current_user: dict = Depends(require_role(["admin", "platform_admin"])),
) -> OrganizationOut:
    """Fetch one organisation by id.

    * ``platform_admin``: any id.
    * ``admin``: only their own (foreign returns 404 to avoid leaking
      whether the org exists).
    """
    if not is_cross_tenant(current_user.get("role")):
        if org_id != current_user["organization_id"]:
            raise HTTPException(status_code=404, detail="Organization not found")
    record = OrganizationRepository.get_by_id(org_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return _to_org_out(record)


@router.post("", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreateRequest,
    current_user: dict = Depends(require_role(["admin", "platform_admin"])),
) -> OrganizationOut:
    """Create a new organisation.

    New orgs start with zero users. The caller stays in their own org
    — only the new row is added. Reserved for a follow-up that may
    auto-create an admin in the new org or offer to transfer the
    caller.
    """
    if OrganizationRepository.get_by_slug(payload.slug) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization slug already exists",
        )
    record = OrganizationRepository.create(name=payload.name, slug=payload.slug)
    return _to_org_out(record)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    org_id: str,
    current_user: dict = Depends(require_role(list(CROSS_TENANT_ROLES))),
) -> None:
    """Delete an organisation.

    Cross-tenant only (derived from ``CROSS_TENANT_ROLES`` so adding
    a new cross-tenant role in one place automatically widens this
    gate). Refuses to drop an organisation with active users (400)
    so an operator cannot accidentally wipe a whole user base. To
    remove an active org, transfer or delete every member first,
    then retry.
    """
    record = OrganizationRepository.get_by_id(org_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    member_count = OrganizationRepository.count_users(org_id)
    if member_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot delete organization with {member_count} "
                f"active user{'s' if member_count != 1 else ''}; "
                "reassign or delete the members first."
            ),
        )
    OrganizationRepository.delete(org_id)
    return None
