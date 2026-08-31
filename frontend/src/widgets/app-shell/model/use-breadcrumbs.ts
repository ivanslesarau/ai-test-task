import { useMatches } from '@tanstack/react-router'

import type { ImpersonationHistorySearch } from '@/entities/impersonation/model/history-search'
import type { DirectorySearch } from '@/entities/user/model/directory-search'

interface BaseCrumb {
  key: string
  label: string
  /** The active route's own crumb renders as plain text, not a link — a
   * breadcrumb never links to the page already on screen. */
  isCurrent: boolean
}

/**
 * A discriminated union, keyed on `to`, rather than a single shape with
 * optional `params`/`search` — this is what lets the consumer render each
 * crumb with the exact `<Link to="..." .../>` overload TanStack Router
 * expects for that route, with no cast at the call site.
 */
export type BreadcrumbCrumb =
  | (BaseCrumb & { to: '/' })
  | (BaseCrumb & { to: '/profile' })
  | (BaseCrumb & { to: '/admin/users'; search: DirectorySearch })
  | (BaseCrumb & { to: '/admin/users/$userId'; params: { userId: string } })
  | (BaseCrumb & { to: '/trainer/portal' })
  | (BaseCrumb & { to: '/trainer/players' })
  | (BaseCrumb & { to: '/family' })
  | (BaseCrumb & { to: '/family/$profileId'; params: { profileId: string } })
  | (BaseCrumb & { to: '/approvals' })
  | (BaseCrumb & { to: '/requests' })
  | (BaseCrumb & { to: '/my-times' })
  | (BaseCrumb & { to: '/availability' })
  | (BaseCrumb & { to: '/trainer/coaches' })
  | (BaseCrumb & { to: '/trainer/coaches/$coachUserId'; params: { coachUserId: string } })
  | (BaseCrumb & { to: '/admin/impersonations'; search: ImpersonationHistorySearch })

/**
 * One label per route that has a page worth naming in the trail. The
 * `/_authed/admin` and `/_authed/trainer` layout routes are deliberately
 * absent — they render only an `<Outlet/>` (see `routes/_authed/admin.tsx`
 * and `routes/_authed/trainer.tsx`), so neither has a page of its own to
 * link to.
 */
const ROUTE_LABELS: Partial<Record<string, string>> = {
  '/_authed/': 'Home',
  '/_authed/profile': 'Profile',
  '/_authed/admin/users/': 'Users',
  '/_authed/admin/users/$userId': 'User',
  '/_authed/trainer/portal': 'Portal settings',
  '/_authed/trainer/players': 'Players',
  '/_authed/family/': 'Family',
  '/_authed/family/$profileId': 'Player',
  '/_authed/approvals': 'Approvals',
  '/_authed/requests': 'Requests',
  '/_authed/my-times': 'My Times',
  '/_authed/availability': 'Availability',
  '/_authed/trainer/coaches/': 'Coaches',
  '/_authed/trainer/coaches/$coachUserId': 'Coach',
  '/_authed/admin/impersonations': 'Impersonation history',
}

const HOME_CRUMB = { key: '/_authed/', label: 'Home', to: '/' } as const

/**
 * Derives the breadcrumb trail from the router's own matched routes as
 * typed link descriptors — no URL is ever built from a string (Principle
 * IV, contracts/frontend-contracts.md §7.3). The `/admin/users` crumb
 * carries the directory's own active search params, so following it back
 * returns to the filtered view rather than a reset one.
 *
 * Home, Profile, and the admin pages are siblings under `_authed`, not
 * literal ancestors of one another, so the router's own matched-route list
 * alone would only ever yield a single-crumb trail. Home is prepended
 * explicitly for every other page — it is the one page every authenticated
 * user can always return to, and the trail is otherwise not a trail at all.
 */
export function useBreadcrumbs(): BreadcrumbCrumb[] {
  const matches = useMatches()
  const pageCrumbs: BreadcrumbCrumb[] = []

  matches.forEach((match, index) => {
    const label = ROUTE_LABELS[match.routeId]
    if (label === undefined) return

    const isCurrent = index === matches.length - 1

    switch (match.routeId) {
      case '/_authed/':
        pageCrumbs.push({ key: match.routeId, label, to: '/', isCurrent })
        break
      case '/_authed/profile':
        pageCrumbs.push({ key: match.routeId, label, to: '/profile', isCurrent })
        break
      case '/_authed/admin/users/':
        pageCrumbs.push({
          key: match.routeId,
          label,
          to: '/admin/users',
          search: match.search as DirectorySearch,
          isCurrent,
        })
        break
      case '/_authed/admin/users/$userId':
        pageCrumbs.push({
          key: match.routeId,
          label,
          to: '/admin/users/$userId',
          params: match.params as { userId: string },
          isCurrent,
        })
        break
      case '/_authed/trainer/portal':
        pageCrumbs.push({ key: match.routeId, label, to: '/trainer/portal', isCurrent })
        break
      case '/_authed/trainer/players':
        pageCrumbs.push({ key: match.routeId, label, to: '/trainer/players', isCurrent })
        break
      case '/_authed/family/':
        pageCrumbs.push({ key: match.routeId, label, to: '/family', isCurrent })
        break
      case '/_authed/family/$profileId':
        pageCrumbs.push({
          key: match.routeId,
          label,
          to: '/family/$profileId',
          params: match.params as { profileId: string },
          isCurrent,
        })
        break
      case '/_authed/approvals':
        pageCrumbs.push({ key: match.routeId, label, to: '/approvals', isCurrent })
        break
      case '/_authed/requests':
        pageCrumbs.push({ key: match.routeId, label, to: '/requests', isCurrent })
        break
      case '/_authed/my-times':
        pageCrumbs.push({ key: match.routeId, label, to: '/my-times', isCurrent })
        break
      case '/_authed/availability':
        pageCrumbs.push({ key: match.routeId, label, to: '/availability', isCurrent })
        break
      case '/_authed/trainer/coaches/':
        pageCrumbs.push({ key: match.routeId, label, to: '/trainer/coaches', isCurrent })
        break
      case '/_authed/trainer/coaches/$coachUserId':
        pageCrumbs.push({
          key: match.routeId,
          label,
          to: '/trainer/coaches/$coachUserId',
          params: match.params as { coachUserId: string },
          isCurrent,
        })
        break
      case '/_authed/admin/impersonations':
        pageCrumbs.push({
          key: match.routeId,
          label,
          to: '/admin/impersonations',
          search: match.search as ImpersonationHistorySearch,
          isCurrent,
        })
        break
      default:
        break
    }
  })

  if (pageCrumbs.length === 0) return []
  if (pageCrumbs[0]?.to === '/') return pageCrumbs
  return [{ ...HOME_CRUMB, isCurrent: false }, ...pageCrumbs]
}
