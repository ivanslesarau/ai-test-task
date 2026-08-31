"""Pure availability business invariants (data-model.md §103, §111.2;
research.md R2-08, R2-21). No I/O and no framework imports here — these
are domain constants the database CHECK constraints
(`ck_availability_slots_*`) and the frontend's Zod schema must both
agree with, following `core/family_rules.py`'s precedent for keeping an
invariant defined exactly once per side of the boundary.

These are NOT configuration: a value that must match a migration's CHECK
constraint cannot be changed by an environment variable without also
shipping a new migration, so it does not belong in `Settings`
(research.md R2-21).
"""

from __future__ import annotations

# The grid every start/end minute must land on (FR-028, R2-08).
MINUTES_PER_SLOT_STEP = 15

# FR-028: at most this many ranges per day.
MAX_SLOTS_PER_DAY = 6

# Monday (0) .. Sunday (6) — data-model.md §103.
DAYS_IN_WEEK = 7

# Minutes from midnight to midnight; a slot may end at 1440 (midnight) but
# never start there (R2-08).
MINUTES_IN_DAY = 1440
