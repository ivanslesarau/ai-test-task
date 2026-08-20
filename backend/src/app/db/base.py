import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def new_uuid() -> str:
    """UUIDv4 as 36-character text (data-model.md §0: chosen over an
    autoincrementing integer so an id can appear in an anonymized email
    address without leaking how many accounts exist)."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Naive datetime holding a UTC value.

    SQLite has no genuine timezone-aware column type — every datetime
    round-trips through it as naive, regardless of what Python object was
    stored. Returning a tz-aware value here would compare successfully
    only until the first database round trip, then raise
    `TypeError: can't compare offset-naive and offset-aware datetimes` the
    moment a freshly-fetched row meets a freshly-computed `utcnow()`. Every
    datetime in this codebase is therefore naive and UTC by convention.
    """
    return datetime.now(UTC).replace(tzinfo=None)
