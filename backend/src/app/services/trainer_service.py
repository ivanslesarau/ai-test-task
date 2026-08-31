from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.enums import PlayerProfileKind
from app.repositories.association_repository import AssociationRepository
from app.repositories.availability_repository import AvailabilityRepository
from app.schemas.availability import AvailabilitySlotModel
from app.schemas.trainer_player import ResponsibleContact, TrainerPlayerPage, TrainerPlayerSummary


def _age_on(dob: date | None, *, today: date) -> int | None:
    if dob is None:
        return None
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


class TrainerService:
    """A trainer's own roster (US6, FR-090, FR-091, FR-116). Deliberately
    carries nothing about a player's other trainers — not an identifier,
    not a count — so no view a trainer can reach discloses that a player
    also trains elsewhere (SC-025), and nothing about any other profile
    on the same account (SC-040)."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._associations = AssociationRepository(db_session)
        self._availability = AvailabilityRepository(db_session)

    async def list_players(
        self, trainer_user_id: str, *, page: int, page_size: int, query: str | None
    ) -> TrainerPlayerPage:
        rows, total = await self._associations.list_for_trainer(
            trainer_user_id, page=page, page_size=page_size, query=query
        )
        today = utcnow().date()

        # US5, research.md R2-12: one `IN` query for the whole page, never
        # one request per row (data-model.md §113).
        slots_by_profile = await self._availability.list_for_profiles(
            [row.player_profile.id for row in rows]
        )

        items = [
            TrainerPlayerSummary(
                player_profile_id=row.player_profile.id,
                # An erased profile already reads "Deleted"/"User" — a
                # child's own row (data-model.md §30) or the responsible
                # account's `user_profiles` row for a SELF profile
                # (FR-045) — so the roster needs no separate erasure
                # check; it simply reflects what is stored (FR-091).
                display_name=(
                    f"{row.player_profile.first_name} {row.player_profile.last_name}"
                    if row.player_profile.kind == PlayerProfileKind.CHILD.value
                    else (
                        f"{row.responsible_account_profile.first_name}"
                        f" {row.responsible_account_profile.last_name}"
                    )
                ),
                kind=PlayerProfileKind(row.player_profile.kind),
                age=_age_on(row.player_profile.date_of_birth, today=today),
                gender=row.player_profile.gender,
                joined_at=row.association.joined_at,
                photo_url=(
                    f"/media/photos/{row.player_profile.photo_key}"
                    if row.player_profile.kind == PlayerProfileKind.CHILD.value
                    and row.player_profile.photo_key
                    else (
                        f"/media/photos/{row.responsible_account_profile.photo_key}"
                        if row.player_profile.kind == PlayerProfileKind.SELF.value
                        and row.responsible_account_profile.photo_key
                        else None
                    )
                ),
                availability=[
                    AvailabilitySlotModel(
                        day_of_week=slot.day_of_week,
                        start_minute=slot.start_minute,
                        end_minute=slot.end_minute,
                    )
                    for slot in slots_by_profile.get(row.player_profile.id, [])
                ],
                availability_updated_at=row.player_profile.availability_updated_at,
                responsible_contact=ResponsibleContact(
                    display_name=(
                        f"{row.responsible_account_profile.first_name}"
                        f" {row.responsible_account_profile.last_name}"
                    ),
                    email=row.responsible_account.email,
                    phone=row.responsible_account_profile.phone,
                ),
            )
            for row in rows
        ]
        return TrainerPlayerPage(items=items, page=page, page_size=page_size, total=total)
