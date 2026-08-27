def render_join_confirmation_email(
    *, first_name: str, trainer_display_name: str
) -> tuple[str, str]:
    """Returns (subject, body) for the confirmation sent after joining a
    trainer through an invitation link (FR-079). A delivery failure must
    not undo the registration or the association, and is never reported
    to the person as a delivery success — the caller (JoinService) only
    records whether this returned True."""
    subject = f"You've joined {trainer_display_name}"
    body = (
        f"Hi {first_name},\n\n"
        f"You're now connected with {trainer_display_name} on PracticePerfect. "
        "You can sign in to see their events and content.\n\n"
        "If you weren't expecting this, contact support."
    )
    return subject, body
