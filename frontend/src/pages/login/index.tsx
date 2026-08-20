import { useNavigate } from "@tanstack/react-router";

import { Route as LoginRoute } from "@/routes/login";
import { SignInForm } from "@/features/auth/sign-in/ui/sign-in-form";
import { landingPathForRole } from "@/entities/session/model/role-guards";
import type { CurrentUser } from "@/shared/api/types";

export function LoginPage() {
  const navigate = useNavigate();
  const { redirect } = LoginRoute.useSearch();

  function handleSuccess(user: CurrentUser) {
    void navigate({ to: redirect ?? landingPathForRole(user.role) });
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-6 p-4">
      <h1 className="text-hero-title">Sign in</h1>
      <SignInForm onSuccess={handleSuccess} />
    </div>
  );
}
