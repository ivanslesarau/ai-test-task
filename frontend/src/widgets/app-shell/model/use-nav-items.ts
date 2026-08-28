import { useApprovals } from '@/entities/approval/api/use-approvals'
import { useSession } from '@/entities/session/api/use-session'
import {
  isChildAccount,
  isPlayerParent,
  isSuperAdmin,
  isTrainer,
} from '@/entities/session/model/role-guards'
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
  | (BaseNavItem & { to: '/family' })
  // The Approvals entry carries a count while any request is pending
  // (FR-159, FR-105) — populated only by the live `useNavItems()` hook;
  // `navItemsForRole`'s static list always carries `count: undefined`,
  // since it has no session to read a count from.
  | (BaseNavItem & { to: '/approvals'; count?: number })
  | (BaseNavItem & { to: '/requests' })

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

// Extension (2026-08-27, family accounts, tasks.md T365, closed by
// T410). D-07 recorded `player_parent`'s empty list as "correct rather
// than missing", because the feature gave them no page beyond
// `/profile`. Family Phase B gave them `/family`; Phase D adds Approvals
// (a parent's decision queue) and Requests (a child's own view) — both
// listed here so `navItemsForRole('player_parent')` proves every route
// reachable for the entry-points regression test (a `player_parent`
// account may be either shape). `useNavItems()` below is what actually
// picks between the two for a live session, on `isChildAccount`.
const PLAYER_PARENT_NAV_ITEMS: NavItem[] = [
  { key: 'family', label: 'Family', to: '/family' },
  { key: 'approvals', label: 'Approvals', to: '/approvals' },
  { key: 'requests', label: 'Requests', to: '/requests' },
]

/**
 * Pure, role-keyed lookup — exported separately from the hook so a
 * regression test (`tests/routes/entry-points.test.tsx`) can enumerate
 * every role's reachable paths without rendering a component.
 *
 * `coach` deliberately resolves to an empty list: this feature gives it
 * no dedicated page beyond `/profile`, and a link to a page that does not
 * exist is worse than no link at all.
 */
export function navItemsForRole(role: UserRole | undefined): NavItem[] {
  switch (role) {
    case 'super_admin':
      return SUPER_ADMIN_NAV_ITEMS
    case 'trainer':
      return TRAINER_NAV_ITEMS
    case 'player_parent':
      return PLAYER_PARENT_NAV_ITEMS
    case 'coach':
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
  const isChild = isChildAccount(user)
  const isParent = isPlayerParent(user) && !isChild

  // Only a parent has a decision queue to badge; a signed-in child skips
  // the request entirely (FR-159).
  const approvals = useApprovals(
    { page: 1, page_size: 1 },
    { enabled: isParent },
  )

  if (isSuperAdmin(user)) return navItemsForRole('super_admin')
  if (isTrainer(user)) return navItemsForRole('trainer')
  if (isPlayerParent(user)) {
    // A parent sees Family and Approvals; a signed-in child sees Family
    // and Requests — never both Approvals and Requests, and never the
    // other role's entry (FR-105, FR-159).
    return navItemsForRole('player_parent')
      .filter((item) => (isChild ? item.to !== '/approvals' : item.to !== '/requests'))
      .map((item) =>
        item.to === '/approvals' ? { ...item, count: approvals.data?.total } : item,
      )
  }
  return []
}
