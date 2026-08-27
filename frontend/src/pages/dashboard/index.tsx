import { Link } from "@tanstack/react-router";

import { useSession } from "@/entities/session/api/use-session";
import type { CurrentUser } from "@/shared/api/types";
import type { NavItem } from "@/widgets/app-shell/model/use-nav-items";
import { useNavItems } from "@/widgets/app-shell/model/use-nav-items";

/**
 * One `<Link .../>` call per item variant — the same per-case switch
 * `PrimaryNav`'s `NavLink` uses, so each route's `to`/`search` combination
 * is checked against the exact overload TanStack Router expects for it
 * (constitution Principle II: no `any`).
 */
function NavEntryLink({ item }: { item: NavItem }) {
  switch (item.to) {
    case "/admin/users":
      return (
        <Link to="/admin/users" search={item.search} className="text-primary underline">
          {item.label}
        </Link>
      );
    case "/trainer/portal":
      return (
        <Link to="/trainer/portal" className="text-primary underline">
          {item.label}
        </Link>
      );
    case "/trainer/players":
      return (
        <Link to="/trainer/players" className="text-primary underline">
          {item.label}
        </Link>
      );
  }
}

function RoleContent({ user, navItems }: { user: CurrentUser; navItems: NavItem[] }) {
  switch (user.role) {
    case "super_admin":
      return (
        <Link to="/admin/users" className="text-primary underline">
          Go to the user directory
        </Link>
      );
    case "player_parent":
      // A player with no association is a valid state (research.md
      // R-24), not an error — a Super Admin-created account, or one
      // whose only trainer was deactivated (FR-089).
      if (user.trainer_count === 0) {
        return (
          <p className="text-muted-foreground">
            You&apos;re not currently connected to a trainer. Ask them for their invitation
            link.
          </p>
        );
      }
      // The active trainer's name, when there is exactly one, is stated
      // by the shell (widgets/trainer-context-switcher/ui/trainer-context-label.tsx,
      // fix F7/T307) rather than duplicated here.
      return <p className="text-muted-foreground">Welcome back.</p>;
    case "trainer":
      // Read from the same descriptor list the header's PrimaryNav reads,
      // so the landing area and the header can never disagree (FR-019,
      // FR-105, fix F7/T306).
      return (
        <div className="flex flex-col gap-2">
          {navItems.map((item) => (
            <NavEntryLink key={item.key} item={item} />
          ))}
        </div>
      );
    case "coach":
      // Each role's own dashboard content is built by later epics; this
      // feature only establishes the landing shell and role branching.
      return <p className="text-muted-foreground">Welcome back.</p>;
  }
}

export function DashboardPage() {
  const { data: user } = useSession();
  const navItems = useNavItems();

  if (!user) return null;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 p-6">
      <RoleContent user={user} navItems={navItems} />
    </div>
  );
}
