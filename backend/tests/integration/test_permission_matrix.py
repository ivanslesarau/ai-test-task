"""The permission matrix SC-002 requires: every role against every
restricted route, asserting 403 and no state change for a role that
doesn't hold it.

This file grows as each story adds restricted routes — US2 (T073), US3
(T096), US4 (T116), US5 (T133) each add entries to RESTRICTED_ROUTES rather
than writing their own separate permission test, so the whole matrix lives
in one place and a reviewer can see the full picture at once.
"""

from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_user

ALL_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.TRAINER,
    UserRole.COACH,
    UserRole.PLAYER_PARENT,
]


class RestrictedRoute:
    """One row of the matrix: a method+path that only `allowed_roles` may
    reach, with a request body factory for methods that need one."""

    def __init__(
        self,
        method: str,
        path_template: str,
        allowed_roles: set[UserRole],
        json_body: dict | None = None,
    ) -> None:
        self.method = method
        self.path_template = path_template
        self.allowed_roles = allowed_roles
        self.json_body = json_body

    def path(self, **kwargs: str) -> str:
        return self.path_template.format(**kwargs)


# US3's /me/profile and /media/photos are role-agnostic (every signed-in
# role may reach them) and are covered by their own tests below instead —
# see test_every_role_can_reach_their_own_profile.
#
RESTRICTED_ROUTES: list[RestrictedRoute] = [
    # US2 — account creation and the user directory are Super-Admin-only.
    RestrictedRoute(
        "POST",
        "/admin/users",
        {UserRole.SUPER_ADMIN},
        json_body={
            "role": "coach",
            "email": "matrix-probe@example.org",
            "first_name": "P",
            "last_name": "Q",
            "phone": "+15551234567",
        },
    ),
    RestrictedRoute("GET", "/admin/users", {UserRole.SUPER_ADMIN}),
    RestrictedRoute("GET", "/admin/users/{user_id}", {UserRole.SUPER_ADMIN}),
    RestrictedRoute("POST", "/admin/users/{user_id}/reinvite", {UserRole.SUPER_ADMIN}),
    RestrictedRoute("GET", "/admin/users/{user_id}/audit", {UserRole.SUPER_ADMIN}),
    # US4 — deactivation and reactivation are Super-Admin-only.
    RestrictedRoute(
        "POST",
        "/admin/users/{user_id}/deactivate",
        {UserRole.SUPER_ADMIN},
        json_body={"version": 1},
    ),
    RestrictedRoute(
        "POST",
        "/admin/users/{user_id}/reactivate",
        {UserRole.SUPER_ADMIN},
        json_body={"version": 1},
    ),
    # US5 — erasure and its compliance record are Super-Admin-only.
    RestrictedRoute(
        "POST",
        "/admin/users/{user_id}/erase",
        {UserRole.SUPER_ADMIN},
        json_body={"version": 1, "reason": "matrix probe"},
    ),
    RestrictedRoute("GET", "/admin/erasure-records/{user_id}", {UserRole.SUPER_ADMIN}),
]


async def _sign_in_as(db_session: AsyncSession, app_client: AsyncClient, role: UserRole) -> None:
    user = await create_user(db_session, role=role)
    token = await create_session_cookie(db_session, user)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)


@pytest.mark.parametrize("role", ALL_ROLES)
async def test_every_role_can_reach_the_session_endpoint(
    app_client: AsyncClient, db_session: AsyncSession, role: UserRole
) -> None:
    """Baseline: the authentication mechanism itself has no accidental
    per-role restriction bug before any role-gated route is tested."""
    await _sign_in_as(db_session, app_client, role)

    response = await app_client.get("/auth/session")

    assert response.status_code == 200
    assert response.json()["role"] == role.value


@pytest.mark.parametrize("role", ALL_ROLES)
async def test_every_role_can_reach_their_own_profile(
    app_client: AsyncClient, db_session: AsyncSession, role: UserRole
) -> None:
    """/me/profile and /media/photos are role-agnostic by design — every
    signed-in person may read and edit their own profile regardless of
    role (US3). The gate here is authentication, not role, which is why
    this route does not belong in RESTRICTED_ROUTES below."""
    await _sign_in_as(db_session, app_client, role)

    response = await app_client.get("/me/profile")

    assert response.status_code == 200
    assert set(response.json()["editable_fields"]) >= {"first_name", "last_name", "phone"}


async def test_me_profile_requires_authentication(app_client: AsyncClient) -> None:
    response = await app_client.get("/me/profile")
    assert response.status_code == 401


async def test_media_photos_requires_authentication(app_client: AsyncClient) -> None:
    response = await app_client.get("/media/photos/nonexistent.png")
    assert response.status_code == 401


@pytest.mark.parametrize("restricted_route", RESTRICTED_ROUTES, ids=lambda r: r.path_template)
@pytest.mark.parametrize("role", ALL_ROLES)
async def test_role_outside_allow_list_is_refused(
    app_client: AsyncClient,
    db_session: AsyncSession,
    role: UserRole,
    restricted_route: RestrictedRoute,
) -> None:
    if role in restricted_route.allowed_roles:
        pytest.skip("role is permitted for this route — covered by the story's own test")

    await _sign_in_as(db_session, app_client, role)

    method: Callable[..., Awaitable] = getattr(app_client, restricted_route.method.lower())
    kwargs = {"json": restricted_route.json_body} if restricted_route.json_body else {}
    response = await method(restricted_route.path(user_id="nonexistent"), **kwargs)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_every_admin_route_is_present_in_the_matrix() -> None:
    """Discovers routes from the app's own generated OpenAPI schema
    rather than trusting the hand-maintained RESTRICTED_ROUTES list to
    stay in sync — a new /admin/* endpoint added without a matching entry
    here fails this test immediately, rather than silently shipping
    unguarded (T144).

    `app.routes` itself is NOT used for this: FastAPI's mounted-router
    entries don't expose a flattened `.path`/`.methods` pair the way a
    resolved OpenAPI path does, so iterating `app.routes` directly finds
    nothing and would make this assertion vacuously true. The generated
    schema (already relied on by test_openapi_contract.py) is the
    reliable source of the app's actual resolved paths.
    """
    from app.main import app

    schema = app.openapi()
    discovered: set[tuple[str, str]] = {
        (method.upper(), path.removeprefix("/api/v1/admin"))
        for path, methods in schema["paths"].items()
        if path.startswith("/api/v1/admin")
        for method in methods
        if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}
    }
    assert discovered, "no /admin routes were discovered — the discovery mechanism is broken"

    covered = {(r.method, r.path_template.removeprefix("/admin")) for r in RESTRICTED_ROUTES}

    missing = discovered - covered
    assert not missing, f"/admin routes with no permission-matrix entry: {missing}"
