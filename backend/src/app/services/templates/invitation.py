def render_invitation_email(*, first_name: str, setup_url: str, ttl_hours: int) -> tuple[str, str]:
    """Returns (subject, body). No password is ever included (FR-025) —
    only a single-use setup link."""
    subject = "You're invited to PracticePerfect"
    body = (
        f"Hi {first_name},\n\n"
        "An account has been created for you on PracticePerfect. "
        "Set your password to get started:\n\n"
        f"{setup_url}\n\n"
        f"This link expires in {ttl_hours} hours and can only be used once.\n\n"
        "If you weren't expecting this invitation, you can ignore this email."
    )
    return subject, body
