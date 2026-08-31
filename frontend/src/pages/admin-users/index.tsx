import { useState } from "react";
import { toast } from "sonner";

import { useUiStore } from "@/app/store/ui-store";
import { useErasureRecord, useUserDetail } from "@/entities/user/api/use-users";
import { CreateUserForm } from "@/features/admin/create-user/ui/create-user-form";
import { DeactivateDialog } from "@/features/admin/deactivate-user/ui/deactivate-dialog";
import { EraseDialog } from "@/features/admin/erase-user/ui/erase-dialog";
import { ImpersonationConfirmDialog } from "@/features/admin/impersonation/ui/impersonation-confirm-dialog";
import { ReactivateDialog } from "@/features/admin/reactivate-user/ui/reactivate-dialog";
import { ReinviteButton } from "@/features/admin/reinvite-user/ui/reinvite-button";
import { Route as UsersIndexRoute } from "@/routes/_authed/admin/users.index";
import { Route as UserDetailRoute } from "@/routes/_authed/admin/users.$userId";
import type { UserRole } from "@/shared/api/types";
import { BackButton } from "@/shared/ui/back-button";
import { Button } from "@/shared/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/shared/ui/dialog";
import { UserDirectoryTable } from "@/widgets/user-directory-table/ui/user-directory-table";

const ROLE_LABEL: Record<UserRole, string> = {
  super_admin: "Super Admin",
  trainer: "Trainer",
  coach: "Coach",
  player_parent: "Player/Parent",
};

export function UsersIndexPage() {
  const search = UsersIndexRoute.useSearch();
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 p-6">
      <BackButton fallbackTo="/" className="self-start" />
      <div className="flex items-center justify-between">
        <h1 className="text-section-title">Users</h1>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>Create user</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create user</DialogTitle>
            </DialogHeader>
            <CreateUserForm
              onSuccess={(result) => {
                setDialogOpen(false);
                toast.success(
                  result.invitation_sent
                    ? `${result.user.first_name} ${result.user.last_name} was created and invited.`
                    : `${result.user.first_name} ${result.user.last_name} was created, but the invitation email could not be sent. Use Re-invite to try again.`,
                );
              }}
            />
          </DialogContent>
        </Dialog>
      </div>
      <UserDirectoryTable search={search} />
      <DeactivateDialog />
      <ReactivateDialog />
      <EraseDialog />
      <ImpersonationConfirmDialog />
    </div>
  );
}

function ErasureRecordPanel({ userId }: { userId: string }) {
  const { data: record, isLoading } = useErasureRecord(userId, true);

  if (isLoading)
    return (
      <p className="text-muted-foreground text-caption">Loading record…</p>
    );
  if (!record) return null;

  return (
    <div className="rounded-md border border-input p-4 text-body">
      <p className="text-card-title">Erasure compliance record</p>
      <dl className="mt-2 grid grid-cols-2 gap-2">
        <dt className="text-muted-foreground">Original email</dt>
        <dd>{record.original_email}</dd>
        <dt className="text-muted-foreground">Original name</dt>
        <dd>
          {record.original_first_name} {record.original_last_name}
        </dd>
        <dt className="text-muted-foreground">Erased by</dt>
        <dd>{record.erased_by.display_name}</dd>
        <dt className="text-muted-foreground">Reason</dt>
        <dd>{record.reason}</dd>
        <dt className="text-muted-foreground">Erased at</dt>
        <dd>{new Date(record.erased_at).toLocaleString()}</dd>
      </dl>
    </div>
  );
}

export function UserDetailPage() {
  const { userId } = UserDetailRoute.useParams();
  const { data: user, isLoading, isError } = useUserDetail(userId);
  const openPendingAction = useUiStore((state) => state.openPendingAction);

  if (isLoading) return <p className="p-6 text-muted-foreground">Loading…</p>;
  if (isError || !user)
    return <p className="p-6 text-destructive">Could not load this user.</p>;

  const isErased = user.status === "deleted";

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4 p-6">
      <BackButton fallbackTo="/admin/users" className="self-start" />
      <h1 className="text-section-title">
        {user.first_name} {user.last_name}
      </h1>
      <dl className="grid grid-cols-2 gap-2 text-body">
        <dt className="text-muted-foreground">Email</dt>
        <dd>{user.email}</dd>
        <dt className="text-muted-foreground">Role</dt>
        <dd>{ROLE_LABEL[user.role]}</dd>
        <dt className="text-muted-foreground">Status</dt>
        <dd>{user.status}</dd>
        <dt className="text-muted-foreground">Created</dt>
        <dd>{new Date(user.created_at).toLocaleDateString()}</dd>
      </dl>
      {/* available_actions is empty for a Deleted account, so this whole
          action row naturally disappears without any status check here —
          the server, not the UI, decided what's possible (FR-048). */}
      <div className="flex gap-2">
        {user.available_actions.includes("reinvite") && (
          <ReinviteButton userId={user.id} />
        )}
        {user.available_actions.includes("deactivate") && (
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              openPendingAction({ kind: "deactivate", userId: user.id })
            }
          >
            Deactivate
          </Button>
        )}
        {user.available_actions.includes("reactivate") && (
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              openPendingAction({ kind: "reactivate", userId: user.id })
            }
          >
            Reactivate
          </Button>
        )}
        {user.available_actions.includes("erase") && (
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              openPendingAction({ kind: "erase", userId: user.id })
            }
          >
            Erase
          </Button>
        )}
      </div>
      {isErased && <ErasureRecordPanel userId={user.id} />}
      <DeactivateDialog />
      <ReactivateDialog />
      <EraseDialog />
      <ImpersonationConfirmDialog />
    </div>
  );
}
