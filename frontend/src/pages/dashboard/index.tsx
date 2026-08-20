import { Link } from "@tanstack/react-router";

import { useSession } from "@/entities/session/api/use-session";
import { useSignOut } from "@/features/auth/sign-out/api/use-sign-out";
import type { CurrentUser, UserRole } from "@/shared/api/types";
import { Button } from "@/shared/ui/button";

const ROLE_LABEL: Record<UserRole, string> = {
  super_admin: "Super Admin",
  trainer: "Trainer",
  coach: "Coach",
  player_parent: "Player/Parent",
};

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
  const signOut = useSignOut();

  if (!user) return null;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 p-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-section-title ">
            {user.first_name} {user.last_name}
          </h1>
          <p className="text-caption text-muted-foreground">
            {ROLE_LABEL[user.role]}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/profile" className="text-body underline">
            Profile
          </Link>
          <Button variant="outline" onClick={() => signOut.mutate()}>
            Sign out
          </Button>
        </div>
      </header>
      <RoleContent user={user} />
    </div>
  );
}
