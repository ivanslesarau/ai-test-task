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
})
