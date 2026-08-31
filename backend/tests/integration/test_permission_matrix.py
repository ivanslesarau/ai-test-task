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
        class _DefaultToNonexistent(dict):
            """Any path placeholder this route needs that the caller did
            not explicitly supply — e.g. `{profile_id}`, `{association_id}`
            — resolves to a harmless placeholder value, the same one
            `{user_id}` has always used. Keeps this table's per-route
            entries free of boilerplate kwargs the role gate never reads
            (extension 2026-08-27: family accounts add path parameters
            other than `user_id` for the first time)."""

            def __missing__(self, key: str) -> str:
                return "nonexistent"

        return self.path_template.format_map(_DefaultToNonexistent(kwargs))


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
            "phone": "+14155552671",
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
    # Extension (2026-08-26) — US6: a trainer's own ShareLink.
    RestrictedRoute("GET", "/me/share-link", {UserRole.TRAINER}),
    RestrictedRoute("POST", "/me/share-link/regenerate", {UserRole.TRAINER}),
    RestrictedRoute("GET", "/trainer/players", {UserRole.TRAINER}),
    # Extension — US7/family accounts: profile-and-trainer context is
    # Player/Parent-only.
    RestrictedRoute("GET", "/me/contexts", {UserRole.PLAYER_PARENT}),
    RestrictedRoute(
        "PUT",
        "/me/context",
        {UserRole.PLAYER_PARENT},
        json_body={"player_profile_id": "nonexistent", "trainer_id": "nonexistent"},
    ),
    # Extension — US8: portal branding is Trainer-only. The two
    # multipart logo endpoints (PUT/DELETE /me/branding/logo) aren't
    # expressible through this table's json_body shape and are covered
    # directly in test_branding_logo.py instead.
    RestrictedRoute("GET", "/me/branding", {UserRole.TRAINER}),
    RestrictedRoute(
        "PATCH", "/me/branding", {UserRole.TRAINER}, json_body={"primary_color": "#3366cc"}
    ),
    RestrictedRoute("POST", "/me/branding/reset", {UserRole.TRAINER}),
    # Extension (2026-08-27) — US9/US10: a family's own player profiles and
    # their trainers are Player/Parent-only at the role gate. Whether a
    # *child's own* sign-in may reach these (FR-132) is a business rule
    # FamilyService enforces, not a role, so it is proven in
    # test_family_profiles.py / test_family_trainers.py instead — this
    # table only proves the other three roles are refused.
    RestrictedRoute("GET", "/me/players", {UserRole.PLAYER_PARENT}),
    RestrictedRoute(
        "POST",
        "/me/players",
        {UserRole.PLAYER_PARENT},
        json_body={
            "first_name": "Probe",
            "last_name": "Child",
            "date_of_birth": "2015-01-01",
            "gender": "male",
        },
    ),
    RestrictedRoute("GET", "/me/players/{profile_id}", {UserRole.PLAYER_PARENT}),
    RestrictedRoute(
        "PATCH",
        "/me/players/{profile_id}",
        {UserRole.PLAYER_PARENT},
        json_body={"school": "Matrix Probe School"},
    ),
    RestrictedRoute("DELETE", "/me/players/{profile_id}", {UserRole.PLAYER_PARENT}),
    RestrictedRoute(
        "POST",
        "/me/players/{profile_id}/trainers",
        {UserRole.PLAYER_PARENT},
        json_body={"trainer_id": "nonexistent"},
    ),
    RestrictedRoute(
        "DELETE", "/me/players/{profile_id}/trainers/{association_id}", {UserRole.PLAYER_PARENT}
    ),
    # Extension (2026-08-27) — US11: a child's own sign-in is Player/Parent
    # -only at the role gate; whether the *caller* may reach it (RequireParentDep,
    # T373) is a business rule proven in test_child_permissions.py, not here.
    RestrictedRoute(
        "PUT",
        "/me/players/{profile_id}/sign-in",
        {UserRole.PLAYER_PARENT},
        json_body={"email": "matrix-child-signin-probe@example.org"},
    ),
    RestrictedRoute("DELETE", "/me/players/{profile_id}/sign-in", {UserRole.PLAYER_PARENT}),
    # Extension (2026-08-27) — US12: the Pending Parent Approval workflow
    # is Player/Parent-only at the role gate, on both sides — a parent's
    # decision queue (`RequireParentDep`) and a child's own raised
    # requests (`PlayerParentOnlyDep`, since a signed-in child is an
    # ordinary player_parent account, research.md R-38). Whether a
    # *specific caller* may reach a *specific* request, and whether a
    # signed-in child is refused the parent-only half despite sharing its
    # role, are business rules proven in test_approval_workflow.py and
    # test_child_permissions_approvals below — this table only proves the
    # other three roles are refused.
    RestrictedRoute("GET", "/me/approvals", {UserRole.PLAYER_PARENT}),
    RestrictedRoute("GET", "/me/approvals/{request_id}", {UserRole.PLAYER_PARENT}),
    RestrictedRoute("POST", "/me/approvals/{request_id}/approve", {UserRole.PLAYER_PARENT}),
    RestrictedRoute("POST", "/me/approvals/{request_id}/deny", {UserRole.PLAYER_PARENT}),
    RestrictedRoute(
        "POST",
        "/me/approvals/{request_id}/request-info",
        {UserRole.PLAYER_PARENT},
        json_body={"note": "matrix probe"},
    ),
    RestrictedRoute("GET", "/me/requests", {UserRole.PLAYER_PARENT}),
    RestrictedRoute("POST", "/me/requests/{request_id}/withdraw", {UserRole.PLAYER_PARENT}),
    RestrictedRoute(
        "POST",
        "/me/requests/{request_id}/respond",
        {UserRole.PLAYER_PARENT},
        json_body={"note": "matrix probe"},
    ),
    # Extension (2026-08-28, spec 002) — US3/US4: a coach's own week is
    # Coach-only at the role gate; a player profile's week is
    # Player/Parent-only, with sibling/child-vs-parent scoping proven by
    # FamilyService instead (test_availability_isolation.py,
    # test_availability_family.py), exactly as the family routes above.
    RestrictedRoute("GET", "/me/availability", {UserRole.COACH}),
    RestrictedRoute(
        "PUT",
        "/me/availability",
        {UserRole.COACH},
        json_body={"slots": []},
    ),
    RestrictedRoute("DELETE", "/me/availability", {UserRole.COACH}),
    RestrictedRoute("GET", "/me/players/{profile_id}/availability", {UserRole.PLAYER_PARENT}),
    RestrictedRoute(
        "PUT",
        "/me/players/{profile_id}/availability",
        {UserRole.PLAYER_PARENT},
        json_body={"slots": []},
    ),
    RestrictedRoute("DELETE", "/me/players/{profile_id}/availability", {UserRole.PLAYER_PARENT}),
    # Extension (2026-08-28, spec 002) — US1: a trainer's own coach
    # invitations are Trainer-only at the role gate; ownership scoping
    # (another trainer's invitation is a 404) is proven separately by
    # test_coach_invite_isolation.py, exactly as the family routes above.
    RestrictedRoute("GET", "/trainer/coach-invitations", {UserRole.TRAINER}),
    RestrictedRoute(
        "POST",
        "/trainer/coach-invitations",
        {UserRole.TRAINER},
        json_body={"email": "matrix-probe@example.org"},
    ),
    RestrictedRoute(
        "POST", "/trainer/coach-invitations/{invitation_id}/resend", {UserRole.TRAINER}
    ),
    RestrictedRoute(
        "POST", "/trainer/coach-invitations/{invitation_id}/revoke", {UserRole.TRAINER}
    ),
    # Extension (2026-08-28, spec 002) — US2: a trainer's own coach roster
    # is Trainer-only at the role gate; ownership scoping (another
    # trainer's coach is a 404) is proven separately by
    # test_coach_roster.py, exactly as the family routes above.
    RestrictedRoute("GET", "/trainer/coaches", {UserRole.TRAINER}),
    RestrictedRoute("DELETE", "/trainer/coaches/{coach_user_id}", {UserRole.TRAINER}),
    # Extension (2026-08-28, spec 002) — US5: a trainer's read of stated
    # times is Trainer-only at the role gate; ownership scoping (another
    # trainer's coach, or a profile with no Active association, is a 404)
    # is proven separately by test_availability_trainer_isolation.py,
    # exactly as the family routes above.
    RestrictedRoute("GET", "/trainer/coaches/{coach_user_id}/availability", {UserRole.TRAINER}),
    RestrictedRoute("GET", "/trainer/players/{profile_id}/availability", {UserRole.TRAINER}),
    # Extension (2026-08-28, spec 002) — US6: starting an impersonation is
    # Super-Admin-only at an ordinary `require_roles` gate, so it fits this
    # table exactly. `DELETE /admin/impersonations/current` deliberately
    # does NOT — research.md R2-15 — and is excluded below with its own
    # dedicated coverage instead (see `_REAL_IDENTITY_ROUTES`).
    RestrictedRoute(
        "POST",
        "/admin/impersonations",
        {UserRole.SUPER_ADMIN},
        json_body={"user_id": "nonexistent"},
    ),
    # Extension (2026-08-28, spec 002) — US7: the append-only impersonation
    # history is Super-Admin-only at an ordinary `require_roles` gate
    # (FR-056), unlike the exit route above.
    RestrictedRoute("GET", "/admin/impersonations", {UserRole.SUPER_ADMIN}),
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


# Extension (2026-08-27) — US12: the parent-only half of the approvals
# workflow refuses a signed-in child despite sharing the player_parent
# role (RequireParentDep, research.md R-38) — a fifth caller shape none
# of RESTRICTED_ROUTES's four-role sweep exercises. The child-only half
# (`/me/requests/*`) must stay reachable, which is the asymmetry this
# test proves alongside the refusal.
_PARENT_ONLY_APPROVAL_ROUTES: list[RestrictedRoute] = [
    r for r in RESTRICTED_ROUTES if r.path_template.startswith("/me/approvals")
]
_CHILD_REACHABLE_REQUEST_ROUTES: list[RestrictedRoute] = [
    r for r in RESTRICTED_ROUTES if r.path_template.startswith("/me/requests")
]


@pytest.mark.parametrize(
    "restricted_route", _PARENT_ONLY_APPROVAL_ROUTES, ids=lambda r: r.path_template
)
async def test_a_signed_in_child_is_refused_the_parent_only_approval_routes(
    app_client: AsyncClient,
    db_session: AsyncSession,
    restricted_route: RestrictedRoute,
) -> None:
    from tests.helpers import create_family
    from tests.helpers import create_session_cookie as _create_session_cookie

    _parent, _profiles, child_accounts = await create_family(
        db_session, children=1, with_sign_in=True
    )
    await db_session.commit()
    token = await _create_session_cookie(db_session, child_accounts[0])
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    method: Callable[..., Awaitable] = getattr(app_client, restricted_route.method.lower())
    kwargs = {"json": restricted_route.json_body} if restricted_route.json_body else {}
    response = await method(restricted_route.path(request_id="nonexistent"), **kwargs)

    assert response.status_code == 403


@pytest.mark.parametrize(
    "restricted_route", _CHILD_REACHABLE_REQUEST_ROUTES, ids=lambda r: r.path_template
)
async def test_a_signed_in_child_can_reach_their_own_requests_routes(
    app_client: AsyncClient,
    db_session: AsyncSession,
    restricted_route: RestrictedRoute,
) -> None:
    """Not 403 — a child raises requests through this same role, and the
    role gate alone (`PlayerParentOnlyDep`) must not turn them away. A
    404 for a nonexistent request id is the expected shape here; only a
    403 would mean the role gate wrongly caught a child."""
    from tests.helpers import create_family
    from tests.helpers import create_session_cookie as _create_session_cookie

    _parent, _profiles, child_accounts = await create_family(
        db_session, children=1, with_sign_in=True
    )
    await db_session.commit()
    token = await _create_session_cookie(db_session, child_accounts[0])
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    method: Callable[..., Awaitable] = getattr(app_client, restricted_route.method.lower())
    kwargs = {"json": restricted_route.json_body} if restricted_route.json_body else {}
    response = await method(restricted_route.path(request_id="nonexistent"), **kwargs)

    assert response.status_code != 403


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
    covered |= {(method, path.removeprefix("/admin")) for method, path in _REAL_IDENTITY_ROUTES}

    missing = discovered - covered
    assert not missing, f"/admin routes with no permission-matrix entry: {missing}"


# Extension (2026-08-28, spec 002) — US6, research.md R2-15:
# `DELETE /admin/impersonations/current` authorizes on the caller's REAL
# identity, not a role — it is reachable by every role, and refuses with
# 404 ("no impersonation in progress") rather than 403 for anyone who
# isn't a Super Admin holding one open. It therefore does not fit this
# table's binary allowed-roles/403 model and is proven directly by
# test_impersonation_exit_timeout.py and test_every_non_admin_role_gets_404_
# not_403_from_the_exit_route below instead.
_REAL_IDENTITY_ROUTES = {("DELETE", "/admin/impersonations/current")}


@pytest.mark.parametrize("role", [UserRole.TRAINER, UserRole.COACH, UserRole.PLAYER_PARENT])
async def test_every_non_admin_role_gets_404_not_403_from_the_exit_route(
    app_client: AsyncClient, db_session: AsyncSession, role: UserRole
) -> None:
    """research.md R2-15: the exit route is not a role gate, so a caller
    who is not a Super Admin (and so can never hold an open impersonation)
    is refused with the same 404 an admin with nothing to exit gets — not
    the 403 every other restricted route in this file returns."""
    await _sign_in_as(db_session, app_client, role)

    response = await app_client.delete("/admin/impersonations/current")

    assert response.status_code == 404


# Extension (2026-08-26): role-agnostic routes every signed-in person may
# reach — not restricted, so they carry no RESTRICTED_ROUTES entry.
_ROLE_AGNOSTIC_ROUTES = {("GET", "/me/profile"), ("PATCH", "/me/profile")}

# The two multipart logo endpoints aren't expressible through
# RestrictedRoute's json_body shape (see the comment beside their
# omission from RESTRICTED_ROUTES above); covered directly in
# test_branding_logo.py instead.
_MULTIPART_ROUTES = {("PUT", "/me/branding/logo"), ("DELETE", "/me/branding/logo")}

# /me/profile/photo is likewise multipart (PUT) and role-agnostic (every
# role); DELETE has no body and needs no json_body entry either way.
_MULTIPART_ROUTES |= {("PUT", "/me/profile/photo"), ("DELETE", "/me/profile/photo")}

# Extension (2026-08-27) — a player profile's photo is multipart too, and
# not expressible through RestrictedRoute's json_body shape; the role gate
# is proven by test_family_photo-shaped assertions in
# test_family_profiles.py instead.
_MULTIPART_ROUTES |= {("PUT", "/me/players/{profile_id}/photo")}


def test_every_me_and_trainer_route_is_present_in_the_matrix_or_accounted_for() -> None:
    """The extension's counterpart to test_every_admin_route_is_present_
    in_the_matrix — /me/* and /trainer/* routes this feature adds are
    role-gated exactly like /admin/*, and a new one must not ship
    unguarded either."""
    from app.main import app

    schema = app.openapi()
    discovered: set[tuple[str, str]] = {
        (method.upper(), path.removeprefix("/api/v1"))
        for path, methods in schema["paths"].items()
        if path.startswith("/api/v1/me/") or path.startswith("/api/v1/trainer/")
        for method in methods
        if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}
    }
    assert discovered, (
        "no /me or /trainer routes were discovered — the discovery mechanism is broken"
    )

    covered = {(r.method, r.path_template) for r in RESTRICTED_ROUTES}
    accounted_for = covered | _ROLE_AGNOSTIC_ROUTES | _MULTIPART_ROUTES

    missing = discovered - accounted_for
    assert not missing, (
        f"/me or /trainer routes with no permission-matrix entry and no documented "
        f"exclusion: {missing}"
    )
