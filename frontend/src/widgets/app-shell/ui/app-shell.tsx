import { Fragment } from "react";

import { Link } from "@tanstack/react-router";

import { useSession } from "@/entities/session/api/use-session";
import { useSignOut } from "@/features/auth/sign-out/api/use-sign-out";
import { resolveMediaUrl } from "@/shared/api/media";
import type { UserRole } from "@/shared/api/types";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/shared/ui/breadcrumb";
import { Button } from "@/shared/ui/button";
import type { BreadcrumbCrumb } from "@/widgets/app-shell/model/use-breadcrumbs";
import { useBreadcrumbs } from "@/widgets/app-shell/model/use-breadcrumbs";
import { TrainerContextSwitcher } from "@/widgets/trainer-context-switcher/ui/trainer-context-switcher";

const ROLE_LABEL: Record<UserRole, string> = {
  super_admin: "Super Admin",
  trainer: "Trainer",
  coach: "Coach",
  player_parent: "Player/Parent",
};

/**
 * One `<BreadcrumbLink asChild><Link .../></BreadcrumbLink>` call per
 * crumb variant. `asChild` clones its *immediate* child, merging in
 * `BreadcrumbLink`'s own props (`data-slot`, `className`) — routing
 * through an intermediate wrapper component that doesn't forward those
 * props would silently drop them, so the real `<Link>` is what sits
 * directly under `asChild` in every branch. The per-case switch (rather
 * than a single generic call) is what keeps every route's
 * `to`/`params`/`search` combination checked against the exact overload
 * TanStack Router expects for it (constitution Principle II: no `any`).
 */
function CrumbLink({ crumb }: { crumb: BreadcrumbCrumb }) {
  switch (crumb.to) {
    case "/":
      return (
        <BreadcrumbLink asChild>
          <Link to="/">{crumb.label}</Link>
        </BreadcrumbLink>
      );
    case "/profile":
      return (
        <BreadcrumbLink asChild>
          <Link to="/profile">{crumb.label}</Link>
        </BreadcrumbLink>
      );
    case "/admin/users":
      return (
        <BreadcrumbLink asChild>
          <Link to="/admin/users" search={crumb.search}>
            {crumb.label}
          </Link>
        </BreadcrumbLink>
      );
    case "/admin/users/$userId":
      return (
        <BreadcrumbLink asChild>
          <Link to="/admin/users/$userId" params={crumb.params}>
            {crumb.label}
          </Link>
        </BreadcrumbLink>
      );
  }
}

/**
 * Persistent header for every authenticated page (`routes/_authed.tsx`
 * only — never `__root.tsx`, which also carries `/login` and
 * `/set-password`). Composes `shared/ui` primitives — a generic
 * from this same widget, the signed-in person's name and role from
 * the `session` query, a typed `/profile` link, and sign-out — and holds
 * no server state of its own; copies nothing into Zustand (constitution
 * Principle IV).
 */
export function AppShell() {
  const { data: user } = useSession();
  const signOut = useSignOut();
  const crumbs = useBreadcrumbs();

  const logoUrl = resolveMediaUrl(user?.portal_branding?.logo_url ?? null);

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-input px-6 py-4">
      <div className="flex items-center gap-3">
        {logoUrl && (
          // <img> only — never <object>/<embed>/inline SVG (research.md R-27).
          <img src={logoUrl} alt="Portal logo" className="h-8 w-8 object-contain" />
        )}
        {crumbs.length > 0 && (
          <Breadcrumb>
            <BreadcrumbList>
              {crumbs.map((crumb, index) => (
                <Fragment key={crumb.key}>
                  {index > 0 && <BreadcrumbSeparator />}
                  <BreadcrumbItem>
                    {crumb.isCurrent ? (
                      <BreadcrumbPage>{crumb.label}</BreadcrumbPage>
                    ) : (
                      <CrumbLink crumb={crumb} />
                    )}
                  </BreadcrumbItem>
                </Fragment>
              ))}
            </BreadcrumbList>
          </Breadcrumb>
        )}
      </div>

      {user && (
        <div className="flex items-center gap-4">
          {user.role === "player_parent" && <TrainerContextSwitcher />}
          <div className="text-right leading-tight">
            <p className="text-body">
              {user.first_name} {user.last_name}
            </p>
            <p className="text-caption text-muted-foreground">
              {ROLE_LABEL[user.role]}
            </p>
          </div>
          <Link to="/profile" className="text-body underline">
            Profile
          </Link>
          <Button variant="outline" onClick={() => signOut.mutate()}>
            Sign out
          </Button>
        </div>
      )}
    </header>
  );
}
