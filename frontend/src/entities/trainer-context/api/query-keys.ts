/**
 * THE context namespace (contracts/frontend-contracts.md §9, §16,
 * research.md R-26, R-47). Every query for data scoped to one player
 * profile and one trainer goes under `['ctx', profileId, trainerId, ...]`
 * — the calendar, token balance, reservation, and content list Epics
 * 02-08 add. A component asking under the new pair's namespace cannot be
 * served the previous pair's cached response, because that response is
 * filed under a different key.
 *
 * **Widened in the family-accounts extension (2026-08-27, tasks.md
 * T337).** FR-117 makes the isolation boundary a *pair*: a key naming
 * only the trainer would collide between two siblings training with the
 * same trainer, and a cached read would leak from one child's view into
 * the other's (research.md R-47). The namespace and the drop-on-switch
 * behaviour (research.md R-26) are otherwise unchanged.
 *
 * The trainer's own roster is not context-scoped this way — a trainer
 * has no profile-and-trainer pair of their own to key it by — and its
 * key moved to `userKeys.roster` (tasks.md T337).
 */
export const ctxKeys = {
  root: ['ctx'] as const,
  scope: (profileId: string, trainerId: string) => ['ctx', profileId, trainerId] as const,
} as const
