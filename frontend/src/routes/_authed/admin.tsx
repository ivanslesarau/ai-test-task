import { Outlet, createFileRoute } from "@tanstack/react-router";

import { useSession } from "@/entities/session/api/use-session";
import { isSuperAdmin } from "@/entities/session/model/role-guards";

function AdminGate() {
  const { data: user } = useSession();

  if (!isSuperAdmin(user)) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-2 text-center">
        <h1 className="text-block-title">
          You don&apos;t have access to this page
        </h1>
        <p className="text-muted-foreground text-body">
          This area is restricted to Super Admins.
        </p>
      </div>
    );
  }

  return <Outlet />;
}

export const Route = createFileRoute("/_authed/admin")({
  component: AdminGate,
});
