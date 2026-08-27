import hashlib
import secrets

from pwdlib import PasswordHash

_password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hasher.verify(password, password_hash)


def generate_token() -> str:
    """A URL-safe random secret for a session cookie or a setup link.

    Only its SHA-256 hash is ever stored (data-model.md §5-6) — the raw
    value exists only in the cookie or the emailed link.
    """
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_share_link_code() -> str:
    """A URL-safe code for a trainer's ShareLink, stored **in clear** —
    unlike every other secret in this module. FR-069 requires the trainer
    to read the code back at any time, which a hash makes impossible, and
    the link is designed to be published on a flyer (research.md R-21).
    128 bits of entropy in 22 characters is the floor FR-066 requires."""
    return secrets.token_urlsafe(16)
