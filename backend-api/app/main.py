import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.repositories import OrganizationRepository, UserRepository
from app.auth.router import router as auth_router
from app.auth.security import hash_password
from app.config import settings
from app.db.session import Base, engine
from app.exceptions import ConflictError
from app.orgs.router import router as orgs_router
from app.users.router import router as users_router

logger = logging.getLogger(__name__)

_DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
)


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOW_ORIGINS", "")
    if not raw:
        return list(_DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


# Hard-coded identifiers for the lazy-bootstrap default org + demo
# users. These match the values the in-memory implementation used so
# any client that has bookmarked them keeps working.
_DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000999"
_DEMO_USER_ID = "00000000-0000-0000-0000-000000000fff"
_DEMO_ADMIN_ID = "00000000-0000-0000-0000-000000000fa1"
_DEMO_SUPPORT_ID = "00000000-0000-0000-0000-000000000fa2"
_DEMO_CUSTOMER_ID = "00000000-0000-0000-0000-000000000fa3"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Boot-time setup.

    1. ``metadata.create_all`` is idempotent and already runs at import
       time via ``app.db``; calling it again here is a no-op and keeps
       the production lifecycle explicit (operators reading the lifespan
       see exactly what happens at boot).
    2. Lazy-bootstrap the default org so the very first ``POST
       /auth/register`` succeeds without an admin having to ``POST
       /organizations`` first.
    3. Seed the demo admin if ``settings.seed_demo_user`` is true AND we
       aren't in production. Short-circuit when the row already exists
       so bcrypt isn't run on every boot.
    """
    Base.metadata.create_all(bind=engine)

    if OrganizationRepository.get_by_slug("default") is None:
        OrganizationRepository.seed(
            id_=_DEFAULT_ORG_ID,
            name="Default",
            slug="default",
        )
        logger.info("Seeded default organisation %s", _DEFAULT_ORG_ID)

    if (
        settings.seed_demo_user
        and settings.environment.lower() != "production"
    ):
        # Seed one demo user per role so a person can test each tier
        # of the RBAC contract end-to-end without a manual setup step.
        # Each is anchored to the default org; the platform_admin slot
        # keeps the cross-tenant scope required for the Organisations
        # page and for transferring users across orgs.
        demo_users = (
            (
                _DEMO_USER_ID,
                "final@aegis.dev",
                "verysecret",
                "platform_admin",
            ),
            (
                _DEMO_ADMIN_ID,
                "admin@aegis.dev",
                "aegis-admin-1!",
                "admin",
            ),
            (
                _DEMO_SUPPORT_ID,
                "support@aegis.dev",
                "aegis-support-1!",
                "support_engineer",
            ),
            (
                _DEMO_CUSTOMER_ID,
                "customer@aegis.dev",
                "aegis-customer-1!",
                "customer",
            ),
        )
        seeded_names: list[str] = []
        for user_id, username, password, role in demo_users:
            if UserRepository.get_by_username(username) is not None:
                continue
            UserRepository.seed(
                id_=user_id,
                username=username,
                password_hash=hash_password(password),
                role=role,
                organization_id=_DEFAULT_ORG_ID,
            )
            seeded_names.append(f"{username}({role})")
        if seeded_names:
            logger.info(
                "Seeded demo users: %s (SEED_DEMO_USER=true)",
                ", ".join(seeded_names),
            )

    yield


app = FastAPI(title="OpsPilot API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ConflictError)
async def _conflict_exception_handler(
    _request: Request, exc: ConflictError
) -> JSONResponse:
    """Translate a repository-level uniqueness violation to HTTP 409.

    Without this handler, a concurrent double-registration for the same
    email would surface as HTTP 500 (the IntegrityError from the unique
    constraint bubbles through ``_session.rollback``). Routers stay
    unchanged because the 409 signal is centralised here.
    """
    return JSONResponse(status_code=409, content={"detail": exc.message})


@app.get("/")
def root():
    return {
        "service": "backend-api",
        "status": "ok",
    }


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(orgs_router)
