"""Fails the build the moment the implementation drifts from the published
contract — every path and method either contract promises must exist in
the generated schema, and the implementation must promise nothing back
that neither contract documents.

**Family accounts extension (2026-08-27, contract v1.2.0, T343).** The
contract is authored as one end-state document that spans several
implementation phases (plan.md §Implementation Sequence for the
extension): Phase A (T321-T344, this file's own phase) reworks the
foundation everything else builds on, and the `family`/`approvals`-tagged
operations are added by Phase B (T348-T353, T372) and Phase C (T397-T398)
respectively. Asserting 1:1 parity against the *whole* contract before
those phases exist would mean this test is red for the length of the
extension, which defeats its purpose as a drift guard for what already
shipped. So the operation-parity checks below are scoped to every tag
this phase's implementation actually owns, and the not-yet-built tags are
named explicitly rather than silently excluded — the same "recorded, not
discovered" treatment R-33 and R-46 already use elsewhere in this
project. Remove the carve-out as each phase closes it.

**Feature 002 extension (2026-08-28, contract v1.3.0, tasks.md T655).**
`specs/002-coach-availability-impersonation/contracts/openapi.yaml` is a
second, purely additive contract file over the same `/api/v1` — it
documents only what 1.3.0 adds, plus the two existing response models
(`CurrentUser`, `TrainerPlayerSummary`) it extends with new optional
fields (research.md R2-22). The implementation as a whole must therefore
match the *union* of both files' operations, not contract 001 alone —
`_all_documented_operations()` below loads and unions both, and every
phase of 002 shipped complete by the time this test file was extended, so
there is no partial-tag carve-out to make for it, unlike the 001
extension above."""

from pathlib import Path

import yaml

from app.main import app

_CONTRACT_001_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "001-user-roles-admin"
    / "contracts"
    / "openapi.yaml"
)

_CONTRACT_002_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "002-coach-availability-impersonation"
    / "contracts"
    / "openapi.yaml"
)

_METHODS = {"get", "post", "put", "patch", "delete"}

# Operations under these tags are not yet implemented — Phase B
# (family_router.py, T348-T353, T372) and Phase C (approvals_router.py,
# T397-T398) add them. Every other tag must already match the contract
# exactly.
_NOT_YET_IMPLEMENTED_TAGS = {"family", "approvals"}

_EXPECTED_OPERATION_COUNT = 51


def _operations(paths: dict) -> set[tuple[str, str]]:
    return {
        (method.upper(), path)
        for path, methods in paths.items()
        for method in methods
        if method in _METHODS
    }


def _operations_excluding_tags(paths: dict, *, excluded_tags: set[str]) -> set[tuple[str, str]]:
    result = set()
    for path, methods in paths.items():
        for method, operation in methods.items():
            if method not in _METHODS:
                continue
            if excluded_tags & set(operation.get("tags", [])):
                continue
            result.add((method.upper(), path))
    return result


def _load_contract() -> dict:
    return yaml.safe_load(_CONTRACT_001_PATH.read_text(encoding="utf-8"))


def _load_contract_002() -> dict:
    return yaml.safe_load(_CONTRACT_002_PATH.read_text(encoding="utf-8"))


def _all_documented_operations() -> set[tuple[str, str]]:
    """The union both contracts promise together (research.md R2-22):
    contract 001's fully-shipped operations (every tag — Epic-01's family
    and approvals slices are both complete by now, so no carve-out
    applies here) plus every operation contract 002 adds. Deduplicated by
    `(method, path)`, which is what correctly folds `GET /auth/session` —
    declared in both files, since 002 only extends its response schema —
    into one entry rather than two."""
    contract_001 = _load_contract()
    contract_002 = _load_contract_002()
    return _operations(contract_001["paths"]) | _operations(contract_002["paths"])


def _generated_operations() -> set[tuple[str, str]]:
    generated = app.openapi()
    # Both contracts' paths omit the /api/v1 prefix main.py adds when
    # mounting each router — strip it for a like-for-like comparison.
    return {
        (method, path.removeprefix("/api/v1")) for method, path in _operations(generated["paths"])
    }


def test_contract_declares_the_expected_operation_count() -> None:
    """The whole end-state document — every phase, every tag — is
    exactly 51 operations (contract v1.2.0, research.md R-49)."""
    contract = _load_contract()
    assert len(_operations(contract["paths"])) == _EXPECTED_OPERATION_COUNT


def test_family_and_approvals_tags_are_declared() -> None:
    contract = _load_contract()
    tag_names = {tag["name"] for tag in contract.get("tags", [])}
    assert {"family", "approvals"} <= tag_names


def test_the_replaced_context_routes_are_gone() -> None:
    """`GET /me/trainers` and `PUT /me/trainer-context` are deleted, not
    deprecated (research.md R-49) — no versioned duplicate survives."""
    contract = _load_contract()
    assert "/me/trainers" not in contract["paths"]
    assert "/me/trainer-context" not in contract["paths"]
    assert "/me/contexts" in contract["paths"]
    assert "/me/context" in contract["paths"]


def test_every_shipped_contract_operation_exists_in_the_implementation() -> None:
    """Every operation either contract promises — contract 001's fully-
    shipped tags plus every operation contract 002 adds — must exist in
    the running app (tasks.md T655)."""
    contract_001 = _load_contract()
    contract_001_ops = _operations_excluding_tags(
        contract_001["paths"], excluded_tags=_NOT_YET_IMPLEMENTED_TAGS
    )
    contract_002_ops = _operations(_load_contract_002()["paths"])
    contract_ops = contract_001_ops | contract_002_ops

    generated_ops = _generated_operations()

    missing = contract_ops - generated_ops
    assert not missing, f"Contract operations missing from the implementation: {missing}"


def test_implementation_has_no_undocumented_operations() -> None:
    """The reverse direction: an endpoint added without updating either
    contract is a drift too, not just a missing one. Not tag-scoped — an
    implementation may never get ahead of the union both contracts
    document (tasks.md T655, research.md R2-22)."""
    contract_ops = _all_documented_operations()
    generated_ops = _generated_operations()

    undocumented = generated_ops - contract_ops
    assert not undocumented, f"Implementation operations missing from the contract: {undocumented}"


def test_contract_002_declares_the_expected_operation_count() -> None:
    """Feature 002's own contract, in isolation: 21 operations across the
    coach-invitations, availability, and impersonation groups, plus the
    one extended existing operation (`GET /auth/session`) — see that
    file's own `info.description` for the three-group breakdown."""
    contract_002 = _load_contract_002()
    assert len(_operations(contract_002["paths"])) == 21


def test_contract_002_tags_are_declared() -> None:
    contract_002 = _load_contract_002()
    tag_names = {tag["name"] for tag in contract_002.get("tags", [])}
    assert {"coach-invitations", "trainer", "availability", "impersonation", "auth"} <= tag_names


def test_every_contract_002_operation_exists_in_the_implementation() -> None:
    """The same parity check as
    `test_every_shipped_contract_operation_exists_in_the_implementation`,
    scoped to contract 002 alone — a narrower, faster-to-diagnose failure
    if only this feature's own operations drift."""
    contract_002_ops = _operations(_load_contract_002()["paths"])
    generated_ops = _generated_operations()

    missing = contract_002_ops - generated_ops
    assert not missing, f"Contract 002 operations missing from the implementation: {missing}"
