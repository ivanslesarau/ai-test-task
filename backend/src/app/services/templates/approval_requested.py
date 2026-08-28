def render_approval_requested_email(
    *,
    child_display_name: str,
    what_is_asked: str,
    amount_minor: int | None,
    currency: str | None,
    review_url: str,
) -> tuple[str, str]:
    """Returns (subject, body) for the parent notification a new approval
    request raises (FR-148). Addressed to the **parent** (research.md
    R-51). `what_is_asked` is the caller's own short description of the
    request's subject — "join Elite Basketball Academy" for a
    `join_trainer` request — so this template stays kind-agnostic rather
    than branching on `kind` itself.

    `join_trainer` requests are raised by `JoinService`, which already
    sends its own more specific email
    (`templates/child_join_request.py`) — this template exists for
    every OTHER path that may one day call `ApprovalService.create`
    directly (a financial kind, once Epic-05 registers its executors)."""
    subject = f"{child_display_name} is asking for your approval"
    amount_line = ""
    if amount_minor is not None and currency is not None:
        amount_line = f"Amount: {amount_minor / 100:.2f} {currency}\n\n"
    body = (
        f"Hi,\n\n"
        f"{child_display_name} wants to {what_is_asked} on PracticePerfect. "
        "This needs your approval before it happens.\n\n"
        f"{amount_line}"
        f"Review this request:\n{review_url}\n\n"
        "If you weren't expecting this, you can ignore this email; nothing happens "
        "until you decide."
    )
    return subject, body
