def render_approval_expired_email_to_parent(
    *, child_display_name: str, what_was_asked: str
) -> tuple[str, str]:
    """Returns (subject, body) telling the **parent** a request lapsed
    unanswered (FR-155). Sent by the maintenance sweep, never by the
    request-time predicate itself (research.md R-43)."""
    subject = f"{child_display_name}'s request expired"
    body = (
        f"Hi,\n\n"
        f"{child_display_name}'s request to {what_was_asked} expired after 48 hours "
        "without a decision. Nothing happened — if this is still needed, "
        f"{child_display_name} can ask again."
    )
    return subject, body


def render_approval_expired_email_to_child(*, what_was_asked: str) -> tuple[str, str]:
    """Returns (subject, body) telling the **child** the same thing
    (FR-155's "MUST notify both the parent and the child")."""
    subject = "Your request expired"
    body = (
        f"Hi,\n\n"
        f"Your request to {what_was_asked} expired after 48 hours without a decision. "
        "Nothing happened — you can ask again if you still want to."
    )
    return subject, body
