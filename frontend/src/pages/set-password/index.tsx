import { useState } from "react";
import { Link } from "@tanstack/react-router";

import { useInvitationCheck } from "@/features/auth/set-password/api/use-setup-password";
import { SetPasswordForm } from "@/features/auth/set-password/ui/set-password-form";
import { Route as SetPasswordRoute } from "@/routes/set-password";
import { isApiError } from "@/shared/api/errors";

export function SetPasswordPage() {
  const { token } = SetPasswordRoute.useSearch();
  const { data, isLoading, isError, error } = useInvitationCheck(token);
  const [done, setDone] = useState(false);

  const linkExpired = isError && isApiError(error) && error.status === 410;

  return (
    <div className="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-6 p-4">
      <h1 className="text-hero-title">Set your password</h1>

      {isLoading && (
        <p className="text-muted-foreground">Checking your invitation…</p>
      )}

      {linkExpired && (
        <p className="text-body">
          This setup link is no longer valid. Ask your Super Admin to send a new
          invitation.
        </p>
      )}

      {isError && !linkExpired && (
        <p className="text-destructive text-body">
          Something went wrong. Try again shortly.
        </p>
      )}

      {data && !done && (
        <>
          <p className="text-body text-muted-foreground">
            Setting up {data.email_hint}
          </p>
          <SetPasswordForm token={token} onSuccess={() => setDone(true)} />
        </>
      )}

      {done && (
        <div className="flex flex-col gap-2">
          <p className="text-body">Your password is set.</p>
          <Link to="/login" className="text-primary underline">
            Sign in
          </Link>
        </div>
      )}
    </div>
  );
}
