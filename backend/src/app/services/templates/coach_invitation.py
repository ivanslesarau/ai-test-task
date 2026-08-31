from datetime import datetime


def render_coach_invitation_email(
    *,
    business_name: str,
    invitee_name: str | None,
    message: str | None,
    invite_url: str,
    expires_at: datetime,
) -> tuple[str, str]:
    """Returns (subject, body) for a trainer's invitation to a prospective
    coach (FR-001, FR-002, FR-003). The raw token exists only inside
    `invite_url` (research.md R2-02) — this function never logs it, and
    neither does anything that calls it."""
    subject = f"{business_name} invited you to coach on PracticePerfect"
    greeting = f"Hi {invitee_name},\n\n" if invitee_name else "Hi,\n\n"
    message_block = f'\n{business_name}\'s message to you:\n"{message}"\n' if message else ""
    body = (
        f"{greeting}"
        f"{business_name} has invited you to join their roster as a coach on PracticePerfect.\n"
        f"{message_block}\n"
        f"Accept the invitation:\n{invite_url}\n\n"
        f"This link expires on {expires_at.date().isoformat()} and can only be used once.\n\n"
        "If you weren't expecting this, you can ignore this email."
    )
    return subject, body
