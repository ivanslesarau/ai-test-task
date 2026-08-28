"""Fails the build the moment the implementation drifts from the published
contract at specs/001-user-roles-admin/contracts/openapi.yaml — every path
and method the contract promises must exist in the generated schema.

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
"""

from pathlib import Path

import yaml

from app.main import app

_CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "001-user-roles-admin"
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
    return yaml.safe_load(_CONTRACT_PATH.read_text(encoding="utf-8"))


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
    contract = _load_contract()
    contract_ops = _operations_excluding_tags(
        contract["paths"], excluded_tags=_NOT_YET_IMPLEMENTED_TAGS
    )

    generated = app.openapi()
    # The contract's paths omit the /api/v1 prefix main.py adds when
    # mounting each router — strip it for a like-for-like comparison.
    generated_ops = {
        (method, path.removeprefix("/api/v1")) for method, path in _operations(generated["paths"])
    }

    missing = contract_ops - generated_ops
    assert not missing, f"Contract operations missing from the implementation: {missing}"


def test_implementation_has_no_undocumented_operations() -> None:
    """The reverse direction: an endpoint added without updating the
    contract is a drift too, not just a missing one. Not tag-scoped — an
    implementation may never get ahead of the contract, even for a tag
    that isn't fully built yet."""
    contract = _load_contract()
    contract_ops = _operations(contract["paths"])

    generated = app.openapi()
    generated_ops = {
        (method, path.removeprefix("/api/v1")) for method, path in _operations(generated["paths"])
    }

    undocumented = generated_ops - contract_ops
    assert not undocumented, f"Implementation operations missing from the contract: {undocumented}"
