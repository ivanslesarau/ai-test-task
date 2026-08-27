import { useState } from 'react'
import { toast } from 'sonner'

import { useOwnShareLink, useRegenerateShareLink } from '@/entities/user/api/use-share-link'
import { isApiError } from '@/shared/api/errors'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/shared/ui/alert-dialog'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'

/**
 * A trainer's standing invitation link: display, copy, and regenerate
 * (US6, FR-065, FR-069). One standing link per trainer — there is no list
 * to manage.
 */
export function ShareLinkPanel() {
  const { data: link, isLoading } = useOwnShareLink()
  const regenerate = useRegenerateShareLink()
  const [confirmOpen, setConfirmOpen] = useState(false)

  async function copyLink() {
    if (!link) return
    try {
      await navigator.clipboard.writeText(link.url)
      toast.success('Link copied.')
    } catch {
      toast.error('Could not copy the link. Copy it manually instead.')
    }
  }

  function handleRegenerate() {
    regenerate.mutate(undefined, {
      onSuccess: () => {
        toast.success('A new link is ready. The old one no longer admits anyone.')
        setConfirmOpen(false)
      },
      onError: (error) => {
        toast.error(isApiError(error) ? error.message : 'Could not create a new link.')
      },
    })
  }

  if (isLoading || !link) {
    return <p className="text-muted-foreground text-body">Loading your invitation link…</p>
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <Input readOnly value={link.url} className="font-mono text-sm" />
        <Button type="button" variant="outline" onClick={copyLink}>
          Copy
        </Button>
      </div>
      <p className="text-muted-foreground text-caption">
        Anyone who opens this link can join your roster. It never expires and has no limit on
        uses. Used {link.use_count} time{link.use_count === 1 ? '' : 's'}.
      </p>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogTrigger asChild>
          <Button type="button" variant="outline" className="self-start">
            Generate a new link
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Replace your invitation link?</AlertDialogTitle>
            <AlertDialogDescription>
              The current link will stop working immediately. Everyone who already joined through
              it stays on your roster — this only affects new joins.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction disabled={regenerate.isPending} onClick={handleRegenerate}>
              {regenerate.isPending ? 'Generating…' : 'Generate new link'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
