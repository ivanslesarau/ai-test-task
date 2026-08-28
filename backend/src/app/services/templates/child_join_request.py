def render_child_join_request_email(
    *, child_display_name: str, trainer_display_name: str, review_url: str
) -> tuple[str, str]:
    """Returns (subject, body) for the parent notification a child's
    blocked join attempt raises (FR-130, FR-138). Addressed to the
    **parent's** address, never the child's (FR-130, research.md R-51) —
    the caller (JoinService) is the one that resolves which address that
    is; this function only names the child and the trainer.

    `review_url` is built by the caller from `settings.frontend_base_url`,
    the same way `render_invitation_email`'s `setup_url` is (there is no
    share-code-derived URL a parent could act on directly, unlike a join
    link itself)."""
    subject = f"{child_display_name} wants to join {trainer_display_name}"
    body = (
        f"Hi,\n\n"
        f"{child_display_name} tried to join {trainer_display_name} on PracticePerfect. "
        "Because this is a child's account, a parent needs to approve it first.\n\n"
        f"Review this request:\n{review_url}\n\n"
        "If you weren't expecting this, you can ignore this email; no one is connected "
        "until you approve it."
    )
    return subject, body
