import type { CurrentUser, UserRole } from '@/shared/api/types'

export function hasRole(user: CurrentUser | undefined, ...roles: UserRole[]): boolean {
  return user !== undefined && roles.includes(user.role)
}

export function isSuperAdmin(user: CurrentUser | undefined): boolean {
  return hasRole(user, 'super_admin')
}

export function isTrainer(user: CurrentUser | undefined): boolean {
  return hasRole(user, 'trainer')
}

/** Extension (2026-08-28, spec 002): a coach's own "My Times" page is
 * Coach-only (FR-024) — the direct counterpart to `isTrainer` above,
 * following the same one-role-one-predicate shape. */
export function isCoach(user: CurrentUser | undefined): boolean {
  return hasRole(user, 'coach')
}

export function isPlayerParent(user: CurrentUser | undefined): boolean {
  return hasRole(user, 'player_parent')
}

/** True when this account is a child's own sign-in — reads the
 * server-derived `is_child_account` field, never inferred from role
 * (a signed-in child is an ordinary `player_parent` account,
 * research.md R-38). Every parent-only control renders through this
 * predicate rather than an inline `session.is_child_account &&`, so the
 * rule has one home (US11/US12, tasks.md T423). */
export function isChildAccount(user: CurrentUser | undefined): boolean {
  return user?.is_child_account ?? false
}

export function landingPathForRole(role: UserRole): string {
  // Every role currently lands on the same dashboard shell, which branches
  // its content by role internally (T067). A distinct path per role can be
  // introduced later without touching this predicate's callers.
  switch (role) {
    case 'super_admin':
    case 'trainer':
    case 'coach':
    case 'player_parent':
      return '/'
  }
}
