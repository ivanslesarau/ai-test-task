from functools import lru_cache
from pathlib import Path

MIN_LENGTH = 12
MAX_LENGTH = 128

_BREACHED_LIST_PATH = Path(__file__).with_name("breached_passwords.txt")


@lru_cache
def _breached_passwords() -> frozenset[str]:
    lines = _BREACHED_LIST_PATH.read_text(encoding="utf-8").splitlines()
    return frozenset(line.strip().lower() for line in lines if line.strip())


def validate_password(password: str) -> str | None:
    """Returns an error message if the password fails policy (FR-014), or
    None if it passes."""
    if len(password) < MIN_LENGTH:
        return f"Password must be at least {MIN_LENGTH} characters."
    if len(password) > MAX_LENGTH:
        return f"Password must be at most {MAX_LENGTH} characters."
    if password.lower() in _breached_passwords():
        return "This password appears in a list of commonly breached passwords. Choose another."
    return None
