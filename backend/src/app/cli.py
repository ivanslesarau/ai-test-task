import argparse
import asyncio
import sys
from datetime import timedelta

from app.core.config import get_settings
from app.core.security import generate_share_link_code, hash_password
from app.db.base import new_uuid, utcnow
from app.db.engine import get_sessionmaker
from app.models.approval import APPROVAL_REQUEST_TTL_HOURS, ApprovalRequest
from app.models.enums import (
    AccountStatus,
    ApprovalRequestKind,
    ApprovalRequestStatus,
    PlayerProfileKind,
    ShareLinkKind,
    UserRole,
)
from app.models.player_profile import PlayerProfile
from app.models.role_details import CoachDetail, ParentContact, TrainerOrganization
from app.models.share_link import ShareLink
from app.models.user import User, UserProfile
from app.repositories.audit_repository import AuditRepository
from app.repositories.user_repository import UserRepository
from app.services.approval_service import ApprovalService
from app.services.maintenance_service import MaintenanceService
from app.services.ports.email_sender import get_email_sender


async def _bootstrap_superadmin() -> int:
    """Create the platform's first Super Admin account.

    Idempotent by refusal: if any Super Admin already exists — in any
    status — this refuses to run, so it can never be used to mint a
    second one. Without this command the platform has no way in, since
    every other account is created by a Super Admin.
    """
    settings = get_settings()
    sessionmaker = get_sessionmaker()

    async with sessionmaker() as db_session:
        users = UserRepository(db_session)
        if await users.any_super_admin_exists():
            print("A Super Admin already exists. Refusing to create another.", file=sys.stderr)
            return 1

        now = utcnow()
        user = User(
            id=new_uuid(),
            email=settings.bootstrap_admin_email.lower(),
            password_hash=hash_password(settings.bootstrap_admin_password),
            role=UserRole.SUPER_ADMIN.value,
            status=AccountStatus.ACTIVE.value,
            version=1,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        await db_session.flush()

        db_session.add(
            UserProfile(
                user_id=user.id,
                first_name="Super",
                last_name="Admin",
                updated_at=now,
            )
        )

        await AuditRepository(db_session).add(
            action="user_created",
            actor_user_id=None,
            target_user_id=user.id,
            detail=f"bootstrap-superadmin CLI: email={user.email}",
        )

        await db_session.commit()

    print(f"Super Admin created: {settings.bootstrap_admin_email}")
    return 0


async def _seed_demo_trainer() -> int:
    """Creates one Trainer with a standing player ShareLink and prints its
    join URL (data-model.md §24, quickstart.md US6). Without this, testing
    registration from a cold start requires signing in as a trainer first
    just to read their link — the loop this command exists to break."""
    settings = get_settings()
    sessionmaker = get_sessionmaker()

    async with sessionmaker() as db_session:
        now = utcnow()
        trainer_email = f"demo-trainer-{new_uuid()}@example.org"
        trainer = User(
            id=new_uuid(),
            email=trainer_email,
            password_hash=hash_password("demo-trainer-password-123456"),
            role=UserRole.TRAINER.value,
            status=AccountStatus.ACTIVE.value,
            version=1,
            created_at=now,
            updated_at=now,
        )
        db_session.add(trainer)
        await db_session.flush()

        db_session.add(
            UserProfile(user_id=trainer.id, first_name="Demo", last_name="Trainer", updated_at=now)
        )
        db_session.add(
            TrainerOrganization(user_id=trainer.id, business_name="Demo Basketball Academy")
        )

        code = generate_share_link_code()
        db_session.add(
            ShareLink(
                id=new_uuid(),
                code=code,
                trainer_user_id=trainer.id,
                created_by_user_id=trainer.id,
                kind=ShareLinkKind.PLAYER_STANDING.value,
                target_email=None,
                expires_at=None,
                max_uses=None,
                use_count=0,
                is_active=True,
                revoked_at=None,
                created_at=now,
            )
        )

        await AuditRepository(db_session).add(
            action="user_created",
            actor_user_id=None,
            target_user_id=trainer.id,
            detail=f"seed-demo-trainer CLI: email={trainer_email}",
        )

        await db_session.commit()

    join_url = f"{settings.frontend_base_url}/join/{code}"
    print(f"Demo trainer created: {trainer_email} / demo-trainer-password-123456")
    print(f"Join URL: {join_url}")
    return 0


async def _seed_demo_family() -> int:
    """Creates a parent with a `self` profile, two children (one with a
    sign-in, one without), a trainer, and one pending `join_trainer`
    request from the signed-in child to that trainer (data-model.md
    §34). The quickstart's US9-US12 walks need a family with a pending
    request, and building one by hand means signing in as a child,
    following a link, and signing back in as the parent before any
    assertion can be made — this command exists to break that loop, the
    same reason `seed-demo-trainer` exists for US6."""
    sessionmaker = get_sessionmaker()

    parent_password = "demo-family-parent-123456"
    child_password = "demo-family-child-123456"

    async with sessionmaker() as db_session:
        now = utcnow()

        parent_email = f"demo-parent-{new_uuid()}@example.org"
        parent = User(
            id=new_uuid(),
            email=parent_email,
            password_hash=hash_password(parent_password),
            role=UserRole.PLAYER_PARENT.value,
            status=AccountStatus.ACTIVE.value,
            version=1,
            created_at=now,
            updated_at=now,
        )
        db_session.add(parent)
        await db_session.flush()
        db_session.add(
            UserProfile(user_id=parent.id, first_name="Demo", last_name="Parent", updated_at=now)
        )
        db_session.add(ParentContact(user_id=parent.id))

        self_profile = PlayerProfile(
            id=new_uuid(),
            account_user_id=parent.id,
            kind=PlayerProfileKind.SELF.value,
            first_name=None,
            last_name=None,
            date_of_birth=now.date() - timedelta(days=366 * 35),
            gender=None,
            tokens_without_approval=False,
            sign_in_user_id=None,
            removed_at=None,
            created_at=now,
            updated_at=now,
        )
        db_session.add(self_profile)

        child_with_signin_email = f"demo-child-{new_uuid()}@example.org"
        child_account = User(
            id=new_uuid(),
            email=child_with_signin_email,
            password_hash=hash_password(child_password),
            role=UserRole.PLAYER_PARENT.value,
            status=AccountStatus.ACTIVE.value,
            version=1,
            created_at=now,
            updated_at=now,
        )
        db_session.add(child_account)
        await db_session.flush()
        db_session.add(
            UserProfile(
                user_id=child_account.id, first_name="Alex", last_name="Demo", updated_at=now
            )
        )

        child_with_signin = PlayerProfile(
            id=new_uuid(),
            account_user_id=parent.id,
            kind=PlayerProfileKind.CHILD.value,
            first_name="Alex",
            last_name="Demo",
            date_of_birth=now.date() - timedelta(days=366 * 10),
            gender=None,
            tokens_without_approval=False,
            sign_in_user_id=child_account.id,
            removed_at=None,
            created_at=now,
            updated_at=now,
        )
        db_session.add(child_with_signin)

        child_without_signin = PlayerProfile(
            id=new_uuid(),
            account_user_id=parent.id,
            kind=PlayerProfileKind.CHILD.value,
            first_name="Maya",
            last_name="Demo",
            date_of_birth=now.date() - timedelta(days=366 * 8),
            gender=None,
            tokens_without_approval=False,
            sign_in_user_id=None,
            removed_at=None,
            created_at=now,
            updated_at=now,
        )
        db_session.add(child_without_signin)

        trainer_email = f"demo-family-trainer-{new_uuid()}@example.org"
        trainer = User(
            id=new_uuid(),
            email=trainer_email,
            password_hash=hash_password("demo-family-trainer-123456"),
            role=UserRole.TRAINER.value,
            status=AccountStatus.ACTIVE.value,
            version=1,
            created_at=now,
            updated_at=now,
        )
        db_session.add(trainer)
        await db_session.flush()
        db_session.add(
            UserProfile(user_id=trainer.id, first_name="Demo", last_name="Trainer", updated_at=now)
        )
        db_session.add(
            TrainerOrganization(user_id=trainer.id, business_name="Demo Family Academy")
        )

        link = ShareLink(
            id=new_uuid(),
            code=generate_share_link_code(),
            trainer_user_id=trainer.id,
            created_by_user_id=trainer.id,
            kind=ShareLinkKind.PLAYER_STANDING.value,
            target_email=None,
            expires_at=None,
            max_uses=None,
            use_count=0,
            is_active=True,
            revoked_at=None,
            created_at=now,
        )
        db_session.add(link)
        await db_session.flush()

        db_session.add(
            ApprovalRequest(
                id=new_uuid(),
                player_profile_id=child_with_signin.id,
                parent_user_id=parent.id,
                kind=ApprovalRequestKind.JOIN_TRAINER.value,
                status=ApprovalRequestStatus.PENDING_PARENT_APPROVAL.value,
                trainer_user_id=trainer.id,
                share_link_id=link.id,
                amount_minor=None,
                currency=None,
                requested_at=now,
                expires_at=now + timedelta(hours=APPROVAL_REQUEST_TTL_HOURS),
                parent_note=None,
                child_note=None,
                resolved_at=None,
                resolved_by_user_id=None,
            )
        )

        await AuditRepository(db_session).add(
            action="user_created",
            actor_user_id=None,
            target_user_id=parent.id,
            detail=f"seed-demo-family CLI: email={parent_email}",
        )

        await db_session.commit()

        # Captured before the session closes: SQLAlchemy expires every
        # loaded object on commit, and a bare attribute read on a
        # detached instance afterward would need a reload the closed
        # session can no longer perform (mirrors the greenlet hazard
        # tests/helpers.py's create_approval_request docstring notes).
        self_profile_id = self_profile.id
        child_with_signin_id = child_with_signin.id
        child_without_signin_id = child_without_signin.id

    print(f"Parent: {parent_email} / {parent_password}")
    print(f"  self profile: {self_profile_id}")
    print(f"Child with sign-in: {child_with_signin_email} / {child_password}")
    print(f"  profile: {child_with_signin_id}")
    print(f"Child with no sign-in profile: {child_without_signin_id}")
    print(f"Trainer: {trainer_email} / demo-family-trainer-123456")
    print("One pending join_trainer request is waiting in the parent's /approvals queue.")
    return 0


async def _prune() -> int:
    """Removes rows whose only purpose was a time-bounded check that has
    already passed (T145) — expired/revoked sessions, old sign-in attempt
    records, and old ShareLink lookup attempt records (extension
    2026-08-26) — and expires lapsed `approval_requests`, notifying both
    the parent and the child of each (FR-155, research.md R-43, extension
    2026-08-27). Never touches audit_entries or erasure_records, which
    are retained indefinitely by design. Must be scheduled at deployment
    (research.md, hourly is sufficient); a request's *unapprovability*
    past 48 hours does not depend on this running, only its notification
    does."""
    settings = get_settings()
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db_session:
        maintenance = MaintenanceService(db_session)
        approval_service = ApprovalService(db_session, settings, get_email_sender(settings))
        sessions_removed = await maintenance.prune_expired_sessions()
        attempts_removed = await maintenance.prune_old_sign_in_attempts()
        link_attempts_removed = await maintenance.prune_old_link_lookup_attempts()
        approvals_expired = await maintenance.expire_lapsed_approval_requests(approval_service)
        await db_session.commit()

    print(
        f"Pruned {sessions_removed} session(s), {attempts_removed} sign-in attempt row(s), "
        f"{link_attempts_removed} link lookup attempt row(s), and expired "
        f"{approvals_expired} lapsed approval request(s)."
    )
    return 0


async def _seed_users(count: int, roles: list[UserRole]) -> int:
    """Seeds `count` Active accounts, split evenly across `roles`, for
    the directory performance check (quickstart.md §4, SC-006). Each
    seeded account has a profile and the matching role detail row, same
    as one created through the API, so the directory query exercises the
    same joins it would in production."""
    sessionmaker = get_sessionmaker()
    now = utcnow()

    async with sessionmaker() as db_session:
        for i in range(count):
            role = roles[i % len(roles)]
            user = User(
                id=new_uuid(),
                email=f"seed-{i}-{new_uuid()}@example.org",
                password_hash=hash_password("111111111111"),
                role=role.value,
                status=AccountStatus.ACTIVE.value,
                version=1,
                created_at=now,
                updated_at=now,
            )
            db_session.add(user)
            db_session.add(
                UserProfile(
                    user_id=user.id,
                    first_name=f"Seed{i}",
                    last_name=role.value,
                    updated_at=now,
                )
            )
            # No ORM relationship() links User to its role-detail table —
            # only a raw FK column — so the flush plan has no dependency
            # edge telling it `users` must insert before `coach_details`
            # etc. Flushing per user makes that order explicit rather
            # than relying on it (and hitting a FOREIGN KEY constraint
            # failed error once inserts are batched by table).
            await db_session.flush()

            if role is UserRole.TRAINER:
                db_session.add(TrainerOrganization(user_id=user.id, business_name=f"Seed Org {i}"))
            elif role is UserRole.COACH:
                db_session.add(CoachDetail(user_id=user.id, is_publicly_visible=False))
            elif role is UserRole.PLAYER_PARENT:
                # No player_profiles row (data-model.md §35) — a seeded
                # account with zero profiles is the same valid shape a
                # Super-Admin-created one has (contract v1.2.0,
                # PlayerParentDetail.profile_count).
                db_session.add(ParentContact(user_id=user.id))

            if (i + 1) % 500 == 0:
                await db_session.flush()

        await db_session.commit()

    print(f"Seeded {count} account(s).")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="app-cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "bootstrap-superadmin", help="Create the platform's first Super Admin account."
    )
    subparsers.add_parser(
        "prune",
        help=(
            "Remove expired sessions and old sign-in/link-lookup attempt records, "
            "and expire lapsed approval requests (notifying parent and child)."
        ),
    )
    seed_parser = subparsers.add_parser(
        "seed-users", help="Seed accounts for the directory performance check."
    )
    seed_parser.add_argument("--count", type=int, required=True)
    seed_parser.add_argument(
        "--roles",
        type=str,
        default="trainer,coach,player_parent",
        help="Comma-separated roles to cycle through.",
    )
    subparsers.add_parser(
        "seed-demo-trainer",
        help="Create one Trainer with a standing ShareLink and print its join URL.",
    )
    subparsers.add_parser(
        "seed-demo-family",
        help=(
            "Create a parent, a self profile, two children (one with a sign-in), a trainer, "
            "and one pending join_trainer request for the US9-US12 quickstart walks."
        ),
    )

    args = parser.parse_args()

    if args.command == "bootstrap-superadmin":
        sys.exit(asyncio.run(_bootstrap_superadmin()))
    elif args.command == "prune":
        sys.exit(asyncio.run(_prune()))
    elif args.command == "seed-users":
        roles = [UserRole(r.strip()) for r in args.roles.split(",")]
        sys.exit(asyncio.run(_seed_users(args.count, roles)))
    elif args.command == "seed-demo-trainer":
        sys.exit(asyncio.run(_seed_demo_trainer()))
    elif args.command == "seed-demo-family":
        sys.exit(asyncio.run(_seed_demo_family()))


if __name__ == "__main__":
    main()
