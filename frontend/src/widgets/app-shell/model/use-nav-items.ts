import { useSession } from '@/entities/session/api/use-session'
import { isSuperAdmin, isTrainer } from '@/entities/session/model/role-guards'
import { directorySearchSchema } from '@/entities/user/model/directory-search'
import type { DirectorySearch } from '@/entities/user/model/directory-search'
import type { UserRole } from '@/shared/api/types'

interface BaseNavItem {
  key: string
  label: string
}

/**
 * A discriminated union on `to`, exactly like `BreadcrumbCrumb` in
 * `use-breadcrumbs.ts` — every consumer renders each item with the exact
 * `<Link to="..." .../>` overload TanStack Router expects for that route,
 * with no URL ever built from a string (Principle IV).
 */
export type NavItem =
  | (BaseNavItem & { to: '/admin/users'; search: DirectorySearch })
  | (BaseNavItem & { to: '/trainer/portal' })
  | (BaseNavItem & { to: '/trainer/players' })

/** The directory's own default view — parsing `{}` reuses the same
 * `.catch()` fallbacks the route's `validateSearch` applies, so this can
 * never drift from what `/admin/users` renders with no query string. */
const DIRECTORY_DEFAULT_SEARCH: DirectorySearch = directorySearchSchema.parse({})

const SUPER_ADMIN_NAV_ITEMS: NavItem[] = [
  { key: 'admin-users', label: 'Users', to: '/admin/users', search: DIRECTORY_DEFAULT_SEARCH },
]

const TRAINER_NAV_ITEMS: NavItem[] = [
  { key: 'trainer-portal', label: 'Portal settings', to: '/trainer/portal' },
  { key: 'trainer-players', label: 'Players', to: '/trainer/players' },
]

/**
 * Pure, role-keyed lookup — exported separately from the hook so a
 * regression test (`tests/routes/entry-points.test.tsx`) can enumerate
 * every role's reachable paths without rendering a component.
 *
 * `coach` and `player_parent` deliberately resolve to an empty list: this
 * feature gives them no dedicated page beyond `/profile` and the trainer
 * switcher, and a link to a page that does not exist is worse than no
 * link at all.
 */
export function navItemsForRole(role: UserRole | undefined): NavItem[] {
  switch (role) {
    case 'super_admin':
      return SUPER_ADMIN_NAV_ITEMS
    case 'trainer':
      return TRAINER_NAV_ITEMS
    case 'coach':
    case 'player_parent':
    case undefined:
      return []
  }
}

/**
 * The single role-aware descriptor list read by both `PrimaryNav` (the
 * header) and the dashboard's landing content, so the two can never
 * disagree about what a role may reach (contracts/frontend-contracts.md
 * §7.3, fix F7). Derived from the `session` query through
 * `entities/session/model/role-guards`, not by switching on `user.role`
 * directly, to keep the guard logic in one place.
 */
export function useNavItems(): NavItem[] {
  const { data: user } = useSession()

  if (isSuperAdmin(user)) return navItemsForRole('super_admin')
  if (isTrainer(user)) return navItemsForRole('trainer')
  return []
}
