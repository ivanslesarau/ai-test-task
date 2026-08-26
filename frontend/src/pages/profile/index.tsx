import { useOwnProfile } from "@/entities/user/api/use-own-profile";
import { EditProfileForm } from "@/features/profile/edit-own/ui/edit-profile-form";
import { PhotoField } from "@/features/profile/edit-own/ui/photo-field";
import { resolveMediaUrl } from "@/shared/api/media";
import { ProfileFormShell } from "@/widgets/profile-form-shell/ui/profile-form-shell";

export function ProfilePage() {
  const { data: profile, isLoading, isError } = useOwnProfile();

  if (isLoading) return <p className="p-6 text-muted-foreground">Loading…</p>;
  if (isError || !profile)
    return <p className="p-6 text-destructive">Could not load your profile.</p>;

  const initials =
    `${profile.first_name[0] ?? ""}${profile.last_name[0] ?? ""}`.toUpperCase();

  return (
    <ProfileFormShell
      title="My profile"
      backTo="/"
      photo={
        <PhotoField photoUrl={resolveMediaUrl(profile.photo_url)} initials={initials} />
      }
    >
      <p className="text-caption text-muted-foreground">{profile.email}</p>
      <EditProfileForm profile={profile} />
    </ProfileFormShell>
  );
}
