import { ImpersonationHistoryTable } from '@/features/admin/impersonation/ui/impersonation-history-table'
import { Route as AdminImpersonationsRoute } from '@/routes/_authed/admin/impersonations'
import { BackButton } from '@/shared/ui/back-button'

/**
 * `/admin/impersonations` (US7, FR-053, FR-054, FR-056). The append-only
 * record of every impersonation the platform has ever permitted,
 * Super-Admin-only.
 */
export function AdminImpersonationsPage() {
  const search = AdminImpersonationsRoute.useSearch()

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 p-6">
      <BackButton fallbackTo="/" className="self-start" />
      <h1 className="text-section-title">Impersonation history</h1>
      <ImpersonationHistoryTable search={search} />
    </div>
  )
}
