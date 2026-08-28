from pydantic import BaseModel, ConfigDict


class TrainerDetailOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_name: str
    address: str | None
    website: str | None
    description: str | None


class CoachDetailOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bio: str | None
    credentials: str | None
    certifications: str | None
    is_publicly_visible: bool


class PlayerParentDetailOut(BaseModel):
    """What remains true of the *account* rather than of any one player on
    it (contract v1.2.0, research.md R-34, R-49): the family's emergency
    contact, held once and serving every child (FR-113), plus a read-only
    count of how many live profiles the account holds. `school`,
    `jersey_number`, and `skill_level` are gone — they describe one
    player, and an account now holds several; they live on `PlayerProfile`
    and are reached through `/me/players`."""

    model_config = ConfigDict(extra="forbid")

    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    emergency_contact_relation: str | None
    profile_count: int


RoleDetailOut = TrainerDetailOut | CoachDetailOut | PlayerParentDetailOut | None


def build_role_detail_out(role_detail_row: object, *, profile_count: int = 0) -> RoleDetailOut:
    """Maps a repository role-detail row (see
    UserRepository.get_role_detail) to its API shape. `profile_count` is
    supplied by the caller — this function does no querying of its own
    (Principle III) — and is ignored for every role but player_parent."""
    from app.models.role_details import CoachDetail, ParentContact, TrainerOrganization

    if role_detail_row is None:
        return None
    if isinstance(role_detail_row, TrainerOrganization):
        return TrainerDetailOut(
            business_name=role_detail_row.business_name,
            address=role_detail_row.address,
            website=role_detail_row.website,
            description=role_detail_row.description,
        )
    if isinstance(role_detail_row, CoachDetail):
        return CoachDetailOut(
            bio=role_detail_row.bio,
            credentials=role_detail_row.credentials,
            certifications=role_detail_row.certifications,
            is_publicly_visible=role_detail_row.is_publicly_visible,
        )
    if isinstance(role_detail_row, ParentContact):
        return PlayerParentDetailOut(
            emergency_contact_name=role_detail_row.emergency_contact_name,
            emergency_contact_phone=role_detail_row.emergency_contact_phone,
            emergency_contact_relation=role_detail_row.emergency_contact_relation,
            profile_count=profile_count,
        )
    raise TypeError(f"Unrecognized role detail row type: {type(role_detail_row)!r}")
