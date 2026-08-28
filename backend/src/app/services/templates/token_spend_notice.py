def render_token_spend_notice_email(
    *, child_display_name: str, what_was_spent: str
) -> tuple[str, str]:
    """Returns (subject, body) for the parent's **informational** notice
    when `tokens_without_approval` is on and a spend proceeds immediately
    (FR-146) — reports what happened, asks for no decision. Addressed to
    the parent (research.md R-51).

    Unwired in this slice: no code path spends a token today (that action
    belongs to Epic-05, research.md R-46), so nothing calls this function
    yet. It exists ahead of that executor for the same reason the
    `token_spend` kind's columns and rules already do — recorded here
    rather than reconstructed later."""
    subject = f"{child_display_name} spent tokens"
    body = (
        f"Hi,\n\n"
        f"{child_display_name} just {what_was_spent} using their token-spending "
        "permission. No action is needed from you — this is just to keep you posted."
    )
    return subject, body
