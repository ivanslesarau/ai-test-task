"""migrate_players_to_profiles

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-27

Extension (family accounts), data step 2 of 3 (data-model.md §33,
research.md R-35). Written with SQLAlchemy Core constructs against
op.get_bind() — not raw SQL — so the two documented raw-SQL exceptions in
plan.md §Complexity Tracking stay at two.

One player_profiles row per player_details row: kind from is_self, names
split from player_name for a child (NULL for a self player), every other
column copied. Then player_profile_id backfilled on every association by
joining player_user_id to the new row's account_user_id. Then one
active_training_contexts row per player whose active_trainer_user_id was
set. Idempotent: re-running selects nothing (guarded by NOT EXISTS).

downgrade() restores player_details rows from player_profiles ONLY when
every account holds exactly one profile, and otherwise RAISES — a
migration that silently discarded a family's second and third child is
worse than one that refuses to run.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _split_name(player_name: str | None) -> tuple[str, str]:
    """Split an existing player_name into (first, last).

    Split on the last space, which is the best a migration can do without
    re-asking the family. A one-word name becomes the first name with '—'
    as the last, because ck_player_profiles_self_names requires a child to
    have both and refusing the migration over a one-word name would block
    the upgrade. Applies only to rows created before this slice; every new
    child supplies both names as separate fields (data-model.md §33).
    """
    name = (player_name or "").strip()
    if not name:
        return ("—", "—")
    if " " not in name:
        return (name, "—")
    first, _, last = name.rpartition(" ")
    return (first.strip() or "—", last.strip() or "—")


def upgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()

    player_details = sa.Table("player_details", metadata, autoload_with=bind)
    player_profiles = sa.Table("player_profiles", metadata, autoload_with=bind)
    associations = sa.Table("trainer_player_associations", metadata, autoload_with=bind)
    contexts = sa.Table("active_training_contexts", metadata, autoload_with=bind)

    # Idempotence guard: skip accounts that already have a profile (a
    # second run of this revision, or a partial prior run).
    already_migrated = {
        row[0] for row in bind.execute(sa.select(player_profiles.c.account_user_id)).fetchall()
    }

    detail_rows = bind.execute(sa.select(player_details)).mappings().fetchall()

    now = _utcnow()
    # account_user_id -> new profile id, for the association and context
    # backfill passes below.
    profile_id_by_account: dict[str, str] = {}

    profile_rows = []
    for detail in detail_rows:
        account_id = detail["user_id"]
        if account_id in already_migrated:
            continue

        profile_id = _new_uuid()
        profile_id_by_account[account_id] = profile_id
        is_self = bool(detail["is_self"])

        if is_self:
            first_name, last_name = None, None
        else:
            first_name, last_name = _split_name(detail["player_name"])

        profile_rows.append(
            {
                "id": profile_id,
                "account_user_id": account_id,
                "kind": "self" if is_self else "child",
                "first_name": first_name,
                "last_name": last_name,
                "photo_key": None,
                "date_of_birth": detail["date_of_birth"],
                "gender": detail["gender"],
                "school": detail["school"],
                "jersey_number": detail["jersey_number"],
                "skill_level": detail["skill_level"],
                "tokens_without_approval": False,
                "sign_in_user_id": None,
                "removed_at": None,
                "created_at": now,
                "updated_at": now,
            }
        )

    if profile_rows:
        bind.execute(sa.insert(player_profiles), profile_rows)

    if not profile_id_by_account:
        # Nothing new to migrate (idempotent re-run with no new accounts).
        # Associations and contexts for previously-migrated accounts were
        # already backfilled on the prior run.
        return

    # Backfill associations for the accounts migrated in this pass.
    account_ids = list(profile_id_by_account.keys())
    assoc_rows = bind.execute(
        sa.select(associations.c.id, associations.c.player_user_id).where(
            associations.c.player_user_id.in_(account_ids),
            associations.c.player_profile_id.is_(None),
        )
    ).fetchall()
    for assoc_id, account_id in assoc_rows:
        bind.execute(
            sa.update(associations)
            .where(associations.c.id == assoc_id)
            .values(player_profile_id=profile_id_by_account[account_id])
        )

    # One active_training_contexts row per player whose active_trainer_user_id
    # was set.
    context_source = bind.execute(
        sa.select(player_details.c.user_id, player_details.c.active_trainer_user_id).where(
            player_details.c.user_id.in_(account_ids),
            player_details.c.active_trainer_user_id.isnot(None),
        )
    ).fetchall()
    context_rows = [
        {
            "user_id": account_id,
            "player_profile_id": profile_id_by_account[account_id],
            "trainer_user_id": trainer_id,
            "updated_at": now,
        }
        for account_id, trainer_id in context_source
    ]
    if context_rows:
        bind.execute(sa.insert(contexts), context_rows)


def downgrade() -> None:
    """Runs after revision 0010's downgrade (Alembic downgrades newest
    first), which has already recreated an EMPTY player_details table and
    an all-NULL player_user_id column on associations. This function's job
    is to populate both from player_profiles — by INSERT, not UPDATE,
    since the target rows do not exist yet."""
    bind = op.get_bind()
    metadata = sa.MetaData()

    player_profiles = sa.Table("player_profiles", metadata, autoload_with=bind)
    player_details = sa.Table("player_details", metadata, autoload_with=bind)
    associations = sa.Table("trainer_player_associations", metadata, autoload_with=bind)
    contexts = sa.Table("active_training_contexts", metadata, autoload_with=bind)

    # A clean reversal is impossible in principle when an account holds
    # more than one profile — player_details is keyed one row per account.
    # Refuse loudly rather than silently discarding a family's second and
    # third child (research.md R-35).
    multi_profile = bind.execute(
        sa.select(player_profiles.c.account_user_id)
        .group_by(player_profiles.c.account_user_id)
        .having(sa.func.count(player_profiles.c.id) > 1)
    ).fetchall()
    if multi_profile:
        offending = [row[0] for row in multi_profile]
        raise RuntimeError(
            "Cannot downgrade past revision 0009: the following accounts hold more than "
            f"one player profile and cannot be represented in player_details: {offending}. "
            "Remove the extra child profiles (and their history) before downgrading, or "
            "accept the data loss explicitly by truncating player_profiles first."
        )

    profile_rows = bind.execute(sa.select(player_profiles)).mappings().fetchall()
    context_by_account = {
        row[0]: row[1]
        for row in bind.execute(sa.select(contexts.c.user_id, contexts.c.trainer_user_id))
    }

    detail_rows = []
    profile_id_by_account: dict[str, str] = {}
    for profile in profile_rows:
        account_id = profile["account_user_id"]
        profile_id_by_account[account_id] = profile["id"]
        is_self = profile["kind"] == "self"
        if is_self:
            player_name = None
        else:
            first = profile["first_name"] or ""
            last = profile["last_name"] or ""
            player_name = f"{first} {last}".strip() or None

        detail_rows.append(
            {
                "user_id": account_id,
                "school": profile["school"],
                "jersey_number": profile["jersey_number"],
                "skill_level": profile["skill_level"],
                "player_name": player_name,
                "date_of_birth": profile["date_of_birth"],
                "gender": profile["gender"],
                "is_self": is_self,
                "active_trainer_user_id": context_by_account.get(account_id),
            }
        )

    if detail_rows:
        bind.execute(sa.insert(player_details), detail_rows)

    # Populate player_user_id on every association from the profile it
    # currently references, using the account each profile belongs to.
    profile_account_by_id = {v: k for k, v in profile_id_by_account.items()}
    assoc_rows = bind.execute(
        sa.select(associations.c.id, associations.c.player_profile_id)
    ).fetchall()
    for assoc_id, profile_id in assoc_rows:
        account_id = profile_account_by_id.get(profile_id)
        if account_id is not None:
            bind.execute(
                sa.update(associations)
                .where(associations.c.id == assoc_id)
                .values(player_user_id=account_id)
            )

    bind.execute(sa.delete(contexts))
    bind.execute(sa.delete(player_profiles))
