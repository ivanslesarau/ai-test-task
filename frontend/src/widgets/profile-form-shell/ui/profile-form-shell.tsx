import type { ReactNode } from "react";

interface ProfileFormShellProps {
  title: string;
  photo: ReactNode;
  children: ReactNode;
}

export function ProfileFormShell({
  title,
  photo,
  children,
}: ProfileFormShellProps) {
  return (
    <div className="mx-auto flex max-w-lg flex-col gap-6 p-6">
      <h1 className="text-section-title">{title}</h1>
      {photo}
      {children}
    </div>
  );
}
