import type { ChangeEvent } from 'react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import {
  useDeleteLogo,
  useOwnBranding,
  useResetBranding,
  useUpdateBranding,
  useUploadLogo,
} from '@/entities/user/api/use-branding'
import { isApiError } from '@/shared/api/errors'
import { resolveMediaUrl } from '@/shared/api/media'
import { brandPalette } from '@/shared/lib/brand-palette'
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
import { FormItem, FormLabel } from '@/shared/ui/form-field'
import { Input } from '@/shared/ui/input'

const DEFAULT_COLOR = '#00b300'

function reportError(error: unknown, fallback: string) {
  toast.error(isApiError(error) ? error.message : fallback)
}

/**
 * A trainer's branding: logo upload with in-place preview, colour picker
 * with live preview, and reset. Both the chosen file and the chosen
 * colour are held as local component state — an `URL.createObjectURL`
 * preview for the logo, a live swatch for the colour — and neither
 * reaches the server, nor the shared BrandingProvider any other viewer
 * reads from, until the trainer presses Save (FR-097).
 */
export function BrandingForm() {
  const { data: branding, isLoading } = useOwnBranding()
  const updateColor = useUpdateBranding()
  const uploadLogo = useUploadLogo()
  const deleteLogo = useDeleteLogo()
  const reset = useResetBranding()

  const [pendingFile, setPendingFile] = useState<File | null>(null)
  const [pendingFileUrl, setPendingFileUrl] = useState<string | null>(null)
  const [pendingColor, setPendingColor] = useState<string | null>(null)

  useEffect(() => {
    if (!pendingFile) {
      setPendingFileUrl(null)
      return
    }
    const url = URL.createObjectURL(pendingFile)
    setPendingFileUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [pendingFile])

  if (isLoading || !branding) {
    return <p className="text-muted-foreground text-body">Loading your branding…</p>
  }

  const savedColor = branding.primary_color ?? DEFAULT_COLOR
  const displayColor = pendingColor ?? savedColor
  const preview = brandPalette(displayColor)
  const savedLogoUrl = resolveMediaUrl(branding.logo_url)
  const displayLogoUrl = pendingFileUrl ?? savedLogoUrl
  const hasPendingChanges = pendingFile !== null || (pendingColor !== null && pendingColor !== savedColor)
  const isSaving = uploadLogo.isPending || updateColor.isPending

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    setPendingFile(file ?? null)
  }

  function handleSave() {
    const tasks: Promise<unknown>[] = []
    if (pendingFile) {
      tasks.push(
        new Promise((resolve, reject) =>
          uploadLogo.mutate(pendingFile, { onSuccess: resolve, onError: reject }),
        ),
      )
    }
    if (pendingColor !== null && pendingColor !== savedColor) {
      tasks.push(
        new Promise((resolve, reject) =>
          updateColor.mutate({ primary_color: pendingColor }, { onSuccess: resolve, onError: reject }),
        ),
      )
    }
    Promise.all(tasks)
      .then(() => {
        toast.success('Branding saved.')
        setPendingFile(null)
        setPendingColor(null)
      })
      .catch((error: unknown) => reportError(error, 'Could not save branding.'))
  }

  return (
    <div className="flex flex-col gap-6">
      <FormItem>
        <FormLabel htmlFor="logo-upload">Logo</FormLabel>
        <div className="flex items-center gap-4">
          {displayLogoUrl ? (
            // <img> only — never <object>/<embed>/inline SVG (research.md R-27).
            <img src={displayLogoUrl} alt="Logo preview" className="h-16 w-16 object-contain" />
          ) : (
            <div className="h-16 w-16 rounded bg-muted" aria-hidden />
          )}
          <div className="flex flex-col gap-2">
            <input
              id="logo-upload"
              type="file"
              accept="image/png,image/jpeg,image/svg+xml"
              onChange={handleFileChange}
              disabled={isSaving}
              className="text-body"
            />
            {savedLogoUrl && !pendingFile && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="self-start"
                disabled={deleteLogo.isPending}
                onClick={() =>
                  deleteLogo.mutate(undefined, {
                    onSuccess: () => toast.success('Logo removed.'),
                    onError: (error) => reportError(error, 'Could not remove the logo.'),
                  })
                }
              >
                Remove logo
              </Button>
            )}
          </div>
        </div>
      </FormItem>

      <FormItem>
        <FormLabel htmlFor="brand-color">Primary colour</FormLabel>
        <div className="flex items-center gap-3">
          <Input
            id="brand-color"
            type="color"
            value={displayColor}
            className="h-10 w-16 p-1"
            onChange={(event) => setPendingColor(event.target.value)}
          />
          <div
            className="h-10 w-24 rounded border border-input"
            style={{ backgroundColor: preview['--brand-primary'] }}
            aria-hidden
          />
        </div>
      </FormItem>

      <Button type="button" className="self-start" disabled={!hasPendingChanges || isSaving} onClick={handleSave}>
        {isSaving ? 'Saving…' : 'Save changes'}
      </Button>

      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button type="button" variant="outline" className="self-start">
            Reset to default
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reset branding?</AlertDialogTitle>
            <AlertDialogDescription>
              Your logo and colour will both return to the platform default. This cannot be
              undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              disabled={reset.isPending}
              onClick={() =>
                reset.mutate(undefined, {
                  onSuccess: () => {
                    toast.success('Branding reset to default.')
                    setPendingFile(null)
                    setPendingColor(null)
                  },
                  onError: (error) => reportError(error, 'Could not reset branding.'),
                })
              }
            >
              {reset.isPending ? 'Resetting…' : 'Reset'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
