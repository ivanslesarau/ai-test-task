import { useRef } from 'react'
import { toast } from 'sonner'

import { useDeleteOwnPhoto, useUploadOwnPhoto } from '@/entities/user/api/use-own-profile'
import { isApiError } from '@/shared/api/errors'
import { Avatar, AvatarFallback, AvatarImage } from '@/shared/ui/avatar'
import { Button } from '@/shared/ui/button'

const MAX_UPLOAD_BYTES = 5 * 1024 * 1024
const ACCEPTED_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp'])

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

    // Client-side pre-checks — the server re-validates by decoding the
    // bytes regardless (research.md R-07); this only saves a round trip
    // for the common mistakes.
    if (!ACCEPTED_TYPES.has(file.type)) {
      toast.error('Upload a JPEG, PNG, or WebP image.')
      return
    }
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
