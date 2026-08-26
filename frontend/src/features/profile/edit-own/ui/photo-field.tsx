import { useRef } from 'react'
import { toast } from 'sonner'

import { useDeleteOwnPhoto, useUploadOwnPhoto } from '@/entities/user/api/use-own-profile'
import { isApiError } from '@/shared/api/errors'
import { Avatar, AvatarFallback, AvatarImage } from '@/shared/ui/avatar'
import { Button } from '@/shared/ui/button'

const MAX_UPLOAD_BYTES = 5 * 1024 * 1024

interface PhotoFieldProps {
  photoUrl: string | null
  initials: string
}

export function PhotoField({ photoUrl, initials }: PhotoFieldProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const upload = useUploadOwnPhoto()
  const remove = useDeleteOwnPhoto()

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

    // Client-side pre-check — the server re-validates by decoding the
    // bytes regardless (research.md R-07), and that decode is the
    // authority on format (R-07). `file.type` is the browser's own
    // extension-based guess: it comes back empty for some OS/browser
    // combinations and unrecognized for others, so it is not hard-checked
    // here — an unsupported format still reaches the server and comes
    // back as a 415 naming the accepted formats.
    if (file.size > MAX_UPLOAD_BYTES) {
      toast.error('Image must be 5 MB or smaller.')
      return
    }

    upload.mutate(file, {
      onError: (error) => toast.error(isApiError(error) ? error.message : 'Upload failed'),
    })
  }

  return (
    <div className="flex items-center gap-4">
      <Avatar className="size-16">
        {photoUrl && <AvatarImage src={photoUrl} alt="" />}
        <AvatarFallback>{initials}</AvatarFallback>
      </Avatar>
      <div className="flex gap-2">
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={handleFileChange}
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={upload.isPending}
          onClick={() => inputRef.current?.click()}
        >
          {upload.isPending ? 'Uploading…' : 'Change photo'}
        </Button>
        {photoUrl && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={remove.isPending}
            onClick={() => remove.mutate()}
          >
            Remove
          </Button>
        )}
      </div>
    </div>
  )
}
