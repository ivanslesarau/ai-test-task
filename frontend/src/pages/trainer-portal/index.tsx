import { BackButton } from '@/shared/ui/back-button'
import { BrandingForm } from '@/features/trainer/branding/ui/branding-form'
import { ShareLinkPanel } from '@/features/trainer/share-link/ui/share-link-panel'

/**
 * One screen carrying both halves of "My Portal Settings" the epic
 * describes — the invitation link a trainer copies, and the branding
 * they set beside it — rather than two routes for what a trainer thinks
 * of as one page.
 */
export function TrainerPortalPage() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 p-6">
      <BackButton fallbackTo="/" className="self-start" />
      <h1 className="text-section-title">Portal settings</h1>

      <section className="flex flex-col gap-2">
        <h2 className="text-block-title">Invitation link</h2>
        <ShareLinkPanel />
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-block-title">Branding</h2>
        <BrandingForm />
      </section>
    </div>
  )
}
