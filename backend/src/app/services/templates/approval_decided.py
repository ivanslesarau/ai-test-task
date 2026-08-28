def render_approval_decided_email(
    *,
    child_display_name: str,
    decision: str,
    what_was_asked: str,
    parent_note: str | None,
) -> tuple[str, str]:
    """Returns (subject, body) telling the **child** what their parent
    decided (FR-150, FR-153) — the exception T395/R-51 carve into "every
    notification is addressed to the parent": this one is the child's own
    status notice. `decision` is `"approved"`, `"denied"`, or
    `"info_requested"`; `parent_note` is included when the parent left
    one, which FR-153 requires the child to see for a denial or an
    information request."""
    verb = {
        "approved": "approved",
        "denied": "denied",
        "info_requested": "asked for more information about",
    }.get(decision, decision)

    subject = f"Your request to {what_was_asked} was {verb}"
    note_line = f'\nYour parent\'s note: "{parent_note}"\n' if parent_note else ""
    body = (
        f"Hi {child_display_name},\n\n"
        f"Your request to {what_was_asked} was {verb}.\n"
        f"{note_line}\n"
        "Sign in to see the full status of everything you've asked for."
    )
    return subject, body
