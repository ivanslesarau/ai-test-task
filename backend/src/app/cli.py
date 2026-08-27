import argparse
import asyncio
import sys

from app.core.config import get_settings
from app.core.security import generate_share_link_code, hash_password
from app.db.base import new_uuid, utcnow
from app.db.engine import get_sessionmaker
from app.models.enums import AccountStatus, ShareLinkKind, UserRole
from app.models.role_details import CoachDetail, ParentContact, PlayerDetail, TrainerOrganization
from app.models.share_link import ShareLink
from app.models.user import User, UserProfile
from app.repositories.audit_repository import AuditRepository
from app.repositories.user_repository import UserRepository
from app.services.maintenance_service import MaintenanceService


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


async def _prune() -> int:
    """Removes rows whose only purpose was a time-bounded check that has
    already passed (T145) — expired/revoked sessions, old sign-in attempt
    records, and old ShareLink lookup attempt records (extension
    2026-08-26). Never touches audit_entries or erasure_records, which
    are retained indefinitely by design."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db_session:
        maintenance = MaintenanceService(db_session)
        sessions_removed = await maintenance.prune_expired_sessions()
        attempts_removed = await maintenance.prune_old_sign_in_attempts()
        link_attempts_removed = await maintenance.prune_old_link_lookup_attempts()
        await db_session.commit()

    print(
        f"Pruned {sessions_removed} session(s), {attempts_removed} sign-in attempt row(s), "
        f"and {link_attempts_removed} link lookup attempt row(s)."
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
                db_session.add(PlayerDetail(user_id=user.id))
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
    subparsers.add_parser("prune", help="Remove expired sessions and old sign-in attempt records.")
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


if __name__ == "__main__":
    main()
