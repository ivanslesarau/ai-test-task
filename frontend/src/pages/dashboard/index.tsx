import { Link } from "@tanstack/react-router";

import { useSession } from "@/entities/session/api/use-session";
import type { CurrentUser } from "@/shared/api/types";

function RoleContent({ user }: { user: CurrentUser }) {
  switch (user.role) {
    case "super_admin":
      return (
        <Link to="/admin/users" className="text-primary underline">
          Go to the user directory
        </Link>
      );
    case "trainer":
    case "coach":
    case "player_parent":
      // Each role's own dashboard content is built by later epics; this
      // feature only establishes the landing shell and role branching.
      return <p className="text-muted-foreground">Welcome back.</p>;
  }
}

export function DashboardPage() {
  const { data: user } = useSession();

  if (!user) return null;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 p-6">
      <RoleContent user={user} />
    </div>
  );
}
