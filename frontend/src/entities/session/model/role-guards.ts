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

export function isPlayerParent(user: CurrentUser | undefined): boolean {
  return hasRole(user, 'player_parent')
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
