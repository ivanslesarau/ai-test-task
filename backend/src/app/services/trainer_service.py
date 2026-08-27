from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.repositories.association_repository import AssociationRepository
from app.schemas.trainer_player import TrainerPlayerPage, TrainerPlayerSummary


def _age_on(dob: date | None, *, today: date) -> int | None:
    if dob is None:
        return None
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


class TrainerService:
    """A trainer's own roster (US6, FR-090, FR-091). Deliberately carries
    nothing about a player's other trainers — not an identifier, not a
    count — so no view a trainer can reach discloses that a player also
    trains elsewhere (SC-025)."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._associations = AssociationRepository(db_session)

    async def list_players(
        self, trainer_user_id: str, *, page: int, page_size: int, query: str | None
    ) -> TrainerPlayerPage:
        rows, total = await self._associations.list_for_trainer(
            trainer_user_id, page=page, page_size=page_size, query=query
        )
        today = utcnow().date()

        items = [
            TrainerPlayerSummary(
                player_user_id=row.player_user.id,
                # An erased account already reads "Deleted User" from its
                # own profile row (FR-045), so the roster needs no
                # separate erasure check — it simply reflects what is
                # stored (FR-091).
                display_name=(
                    row.player_detail.player_name
                    if row.player_detail is not None and row.player_detail.player_name
                    else f"{row.player_profile.first_name} {row.player_profile.last_name}"
                ),
                is_self=row.player_detail.is_self if row.player_detail is not None else True,
                age=_age_on(
                    row.player_detail.date_of_birth if row.player_detail is not None else None,
                    today=today,
                ),
                gender=row.player_detail.gender if row.player_detail is not None else None,
                joined_at=row.association.joined_at,
                photo_url=(
                    f"/media/photos/{row.player_profile.photo_key}"
                    if row.player_profile.photo_key
                    else None
                ),
            )
            for row in rows
        ]
        return TrainerPlayerPage(items=items, page=page, page_size=page_size, total=total)
