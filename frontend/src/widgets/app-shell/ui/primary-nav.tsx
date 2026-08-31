import { Link } from '@tanstack/react-router'

import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import type { NavItem } from '@/widgets/app-shell/model/use-nav-items'
import { useNavItems } from '@/widgets/app-shell/model/use-nav-items'

const ACTIVE_CLASS_NAME = 'bg-accent text-accent-foreground'

/**
 * One `<Button asChild><Link .../></Button>` call per item variant — the
 * same per-case switch `CrumbLink` uses in `app-shell.tsx`, and for the
 * same reason: it is what keeps every route's `to`/`search` combination
 * checked against the exact overload TanStack Router expects for it
 * (constitution Principle II: no `any`).
 */
function NavLink({ item }: { item: NavItem }) {
  switch (item.to) {
    case '/admin/users':
      return (
        <Button asChild variant="ghost" size="sm">
          <Link
            to="/admin/users"
            search={item.search}
            activeOptions={{ includeSearch: false }}
            activeProps={{ className: ACTIVE_CLASS_NAME }}
          >
            {item.label}
          </Link>
        </Button>
      )
    case '/trainer/portal':
      return (
        <Button asChild variant="ghost" size="sm">
          <Link to="/trainer/portal" activeProps={{ className: ACTIVE_CLASS_NAME }}>
            {item.label}
          </Link>
        </Button>
      )
    case '/trainer/players':
      return (
        <Button asChild variant="ghost" size="sm">
          <Link to="/trainer/players" activeProps={{ className: ACTIVE_CLASS_NAME }}>
            {item.label}
          </Link>
        </Button>
      )
    case '/family':
      return (
        <Button asChild variant="ghost" size="sm">
          <Link to="/family" activeProps={{ className: ACTIVE_CLASS_NAME }}>
            {item.label}
          </Link>
        </Button>
      )
    case '/approvals':
      return (
        <Button asChild variant="ghost" size="sm">
          <Link to="/approvals" activeProps={{ className: ACTIVE_CLASS_NAME }}>
            {item.label}
            {Boolean(item.count) && <Badge variant="secondary">{item.count}</Badge>}
          </Link>
        </Button>
      )
    case '/requests':
      return (
        <Button asChild variant="ghost" size="sm">
          <Link to="/requests" activeProps={{ className: ACTIVE_CLASS_NAME }}>
            {item.label}
          </Link>
        </Button>
      )
    case '/my-times':
      return (
        <Button asChild variant="ghost" size="sm">
          <Link to="/my-times" activeProps={{ className: ACTIVE_CLASS_NAME }}>
            {item.label}
          </Link>
        </Button>
      )
    case '/availability':
      return (
        <Button asChild variant="ghost" size="sm">
          <Link to="/availability" activeProps={{ className: ACTIVE_CLASS_NAME }}>
            {item.label}
          </Link>
        </Button>
      )
    case '/trainer/coaches':
      return (
        <Button asChild variant="ghost" size="sm">
          <Link to="/trainer/coaches" activeProps={{ className: ACTIVE_CLASS_NAME }}>
            {item.label}
          </Link>
        </Button>
      )
    case '/admin/impersonations':
      return (
        <Button asChild variant="ghost" size="sm">
          <Link
            to="/admin/impersonations"
            search={item.search}
            activeOptions={{ includeSearch: false }}
            activeProps={{ className: ACTIVE_CLASS_NAME }}
          >
            {item.label}
          </Link>
        </Button>
      )
  }
}

/**
 * The header's primary navigation region — every capability T301's
 * descriptor list grants the signed-in role, rendered as real `<Link>`s
 * (FR-105). Renders nothing at all, not an empty bar, when the list is
 * empty — which no role's list is any longer as of spec 002 (`coach`
 * gained My Times, FR-024), but the guard stays for any future role
 * `navItemsForRole` returns `[]` for.
 *
 * These links are a rendering decision only, never a permission boundary
 * — every target is guarded again by its own route and again by the
 * server (FR-015).
 */
export function PrimaryNav() {
  const items = useNavItems()

  if (items.length === 0) return null

  return (
    <nav aria-label="Primary" className="flex items-center gap-1">
      {items.map((item) => (
        <NavLink key={item.key} item={item} />
      ))}
    </nav>
  )
}
