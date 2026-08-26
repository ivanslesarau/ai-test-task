import type { ReactNode } from "react";

import type { LinkProps } from "@tanstack/react-router";

import { BackButton } from "@/shared/ui/back-button";

interface ProfileFormShellProps {
  title: string;
  photo: ReactNode;
  children: ReactNode;
  /** Optional: not every page that composes this shell has somewhere
   * sensible to go back to. When given, renders a `BackButton` above the
   * title. */
  backTo?: LinkProps["to"];
}

export function ProfileFormShell({
  title,
  photo,
  children,
  backTo,
}: ProfileFormShellProps) {
  return (
    <div className="mx-auto flex max-w-lg flex-col gap-6 p-6">
      {backTo !== undefined && <BackButton fallbackTo={backTo} className="self-start" />}
      <h1 className="text-section-title">{title}</h1>
      {photo}
      {children}
    </div>
  );
}
