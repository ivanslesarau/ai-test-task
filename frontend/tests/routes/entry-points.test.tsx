import { createRouter } from '@tanstack/react-router'
import { describe, expect, it } from 'vitest'

import { routeTree } from '@/routeTree.gen'
import type { UserRole } from '@/shared/api/types'
import { navItemsForRole } from '@/widgets/app-shell/model/use-nav-items'

/**
 * Orphan-route regression gate (fix F7). Every authenticated path is
 * discovered from the app's own route table — `router.routesById`,
 * resolved from `frontend/src/routeTree.gen.ts` — the same way
 * `backend/tests/integration/test_trainer_isolation.py` (T255) discovers
 * backend routes, rather than by hand-listing them here. A route added by
 * a later epic with no entry point fails this test.
 *
 * A path is considered reachable if it is one of T301's per-role nav
 * descriptors (`navItemsForRole`), which is also what T306's dashboard
 * landing content renders for a Trainer — or if it is explicitly
 * allow-listed below as correctly reached another way.
 */
const ALLOW_LISTED_PATHS = new Set<string>([
  // The landing page itself — every role lands here after sign-in; there
  // is nothing to "link to" for the page you always start on.
  '/',
  // The shell's own persistent Profile link (app-shell.tsx).
  '/profile',
  // Layout routes: each renders only an `<Outlet/>` (see
  // routes/_authed/admin.tsx and routes/_authed/trainer.tsx) and has no
  // page of its own to link to — the same reasoning use-breadcrumbs.ts
  // already applies to `/_authed/admin`.
  '/admin',
  '/trainer',
  // A directory row action (widgets/user-directory-table), not a nav
  // entry point.
  '/admin/users/$userId',
  // A family roster row action (widgets/family-roster-list), not a nav
  // entry point — same shape as '/admin/users/$userId' above (extension
  // 2026-08-27, tasks.md T364).
  '/family/$profileId',
  // A coach roster row action (features/trainer/coaches/coach-roster-table),
  // not a nav entry point — same shape as '/admin/users/$userId' above
  // (US5, tasks.md T611).
  '/trainer/coaches/$coachUserId',
])

const ALL_ROLES: UserRole[] = ['super_admin', 'trainer', 'coach', 'player_parent']

function normalize(path: string): string {
  if (path.length > 1 && path.endsWith('/')) return path.slice(0, -1)
  return path
}

describe('entry points', () => {
  it('has a click path for every authenticated route', () => {
    const router = createRouter({ routeTree })

    const reachableFromNav = new Set(
      ALL_ROLES.flatMap((role) => navItemsForRole(role).map((item) => item.to)),
    )

    // Every route under the `_authed` layout except the bare layout id
    // itself, which shares its full path with `/_authed/` (the index
    // route) and is not a distinct page.
    const authedRouteIds = Object.keys(router.routesById).filter(
      (id) => id.startsWith('/_authed') && id !== '/_authed',
    )
    expect(authedRouteIds.length).toBeGreaterThan(0)

    const unreachable = authedRouteIds.filter((id) => {
      const route = router.routesById[id as keyof typeof router.routesById]
      const path = normalize(route.fullPath)
      return !ALLOW_LISTED_PATHS.has(path) && !reachableFromNav.has(path)
    })

    expect(unreachable).toEqual([])
  })

  // Extension (2026-08-28, spec 002, US3): `coach` used to resolve to an
  // empty list — this feature gives it its own page (FR-024).
  it("gives a coach a click path to My Times", () => {
    const paths = navItemsForRole('coach').map((item) => item.to)
    expect(paths).toContain('/my-times')
  })

  // Extension (2026-08-28, spec 002, US4): Availability is listed for
  // `player_parent` unconditionally — both the parent shape and the
  // signed-in-child shape of that role reach it (frontend-contracts.md
  // §36), unlike Approvals/Requests, which `useNavItems()` filters by
  // `isChildAccount` at render time.
  it('gives both parent and child variants of player_parent a click path to Availability', () => {
    const paths = navItemsForRole('player_parent').map((item) => item.to)
    expect(paths).toContain('/availability')
  })

  // Extension (2026-08-28, spec 002, US1): a trainer's reachable-path set
  // includes Coaches (FR-001 – FR-010, FR-020, FR-021).
  it('gives a trainer a click path to Coaches', () => {
    const paths = navItemsForRole('trainer').map((item) => item.to)
    expect(paths).toContain('/trainer/coaches')
  })

  // Extension (2026-08-28, spec 002, US7): a Super Admin's reachable-path
  // set includes the impersonation history (FR-053, FR-054, FR-056).
  it('gives a Super Admin a click path to the impersonation history', () => {
    const paths = navItemsForRole('super_admin').map((item) => item.to)
    expect(paths).toContain('/admin/impersonations')
  })
})
