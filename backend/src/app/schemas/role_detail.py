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
    model_config = ConfigDict(extra="forbid")

    school: str | None
    jersey_number: str | None
    skill_level: str | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    emergency_contact_relation: str | None


RoleDetailOut = TrainerDetailOut | CoachDetailOut | PlayerParentDetailOut | None


def build_role_detail_out(role_detail_row: object) -> RoleDetailOut:
    """Maps a repository role-detail row (see
    UserRepository.get_role_detail) to its API shape."""
    from app.models.role_details import (
        CoachDetail,
        ParentContact,
        PlayerDetail,
        TrainerOrganization,
    )

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
    if isinstance(role_detail_row, tuple):
        player, parent = role_detail_row
        assert isinstance(player, PlayerDetail)
        assert parent is None or isinstance(parent, ParentContact)
        return PlayerParentDetailOut(
            school=player.school,
            jersey_number=player.jersey_number,
            skill_level=player.skill_level,
            emergency_contact_name=parent.emergency_contact_name if parent else None,
            emergency_contact_phone=parent.emergency_contact_phone if parent else None,
            emergency_contact_relation=parent.emergency_contact_relation if parent else None,
        )
    raise TypeError(f"Unrecognized role detail row type: {type(role_detail_row)!r}")
