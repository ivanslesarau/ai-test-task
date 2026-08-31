/**
 * One namespace, one discriminated subject — never two parallel key
 * families, because the week is one concept with two kinds of owner
 * (research.md R2-07, frontend-contracts.md §31). All four subject kinds
 * are declared here even though US3/US4 (this phase) implement only
 * `own` and `profile`; `coach-as-trainer`/`player-as-trainer` are US5's
 * read-only trainer views, added later without touching this file's
 * shape.
 */
export type AvailabilitySubject =
  | { kind: 'own' }
  | { kind: 'profile'; profileId: string }
  | { kind: 'coach-as-trainer'; coachUserId: string }
  | { kind: 'player-as-trainer'; profileId: string }

export const availabilityKeys = {
  all: ['availability'] as const,
  week: (subject: AvailabilitySubject) => ['availability', 'week', subject] as const,
}

/** The one place an `AvailabilitySubject` becomes a URL — reused by every
 * hook in this entity so there is exactly one mapping to keep in sync
 * with `contracts/openapi.yaml`'s four `.../availability` operations
 * (research.md R2-11: each subject nests under the resource that already
 * owns its authorization, never a polymorphic `?subject_kind=` query). */
export function availabilitySubjectUrl(subject: AvailabilitySubject): string {
  switch (subject.kind) {
    case 'own':
      return '/me/availability'
    case 'profile':
      return `/me/players/${subject.profileId}/availability`
    case 'coach-as-trainer':
      return `/trainer/coaches/${subject.coachUserId}/availability`
    case 'player-as-trainer':
      return `/trainer/players/${subject.profileId}/availability`
  }
}

/** `own` and `profile` are the only subjects with a write side (US3,
 * US4) — the trainer-facing subjects are read-only by contract (FR-037):
 * no `PUT`/`DELETE` operation exists for them, so `use-save-availability`
 * and `use-clear-availability` are typed to refuse them at compile time
 * rather than at a runtime check. */
export type WritableAvailabilitySubject = Extract<
  AvailabilitySubject,
  { kind: 'own' } | { kind: 'profile' }
>
