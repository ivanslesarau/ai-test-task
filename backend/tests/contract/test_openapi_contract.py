"""Fails the build the moment the implementation drifts from the published
contract at specs/001-user-roles-admin/contracts/openapi.yaml — every path
and method the contract promises must exist in the generated schema."""

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


def _operations(paths: dict) -> set[tuple[str, str]]:
    return {
        (method.upper(), path)
        for path, methods in paths.items()
        for method in methods
        if method in _METHODS
    }


def test_every_contract_operation_exists_in_the_implementation() -> None:
    contract = yaml.safe_load(_CONTRACT_PATH.read_text(encoding="utf-8"))
    contract_ops = _operations(contract["paths"])

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
    contract is a drift too, not just a missing one."""
    contract = yaml.safe_load(_CONTRACT_PATH.read_text(encoding="utf-8"))
    contract_ops = _operations(contract["paths"])

    generated = app.openapi()
    generated_ops = {
        (method, path.removeprefix("/api/v1")) for method, path in _operations(generated["paths"])
    }

    undocumented = generated_ops - contract_ops
    assert not undocumented, f"Implementation operations missing from the contract: {undocumented}"
