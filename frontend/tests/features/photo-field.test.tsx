import type { ComponentProps } from 'react'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PhotoField } from '@/features/profile/edit-own/ui/photo-field'

import { server } from '../msw-server'

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}))

// jsdom never fires the `load`/`error` events Radix Avatar's `Image` waits
// for before rendering an `<img>`, since nothing actually fetches
// `photoUrl`. Swapping in a plain `<img>` here is the only way to assert
// on the resolved `src` without faking image-load events for every test.
vi.mock('radix-ui', async (importOriginal) => {
  const actual = await importOriginal<typeof import('radix-ui')>()
  return {
    ...actual,
    Avatar: {
      ...actual.Avatar,
      Image: (props: ComponentProps<'img'>) => <img {...props} alt="" />,
    },
  }
})

beforeEach(() => {
  vi.clearAllMocks()
})

function renderField(photoUrl: string | null = null) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <PhotoField photoUrl={photoUrl} initials="AB" />
    </QueryClientProvider>,
  )
}

/**
 * `userEvent.upload`'s default `applyAccept: true` mimics a native file
 * picker, silently dropping any file that doesn't match the input's
 * `accept` attribute — an empty or unrecognized `file.type` never reaches
 * the change handler at all under that default. Real browsers apply that
 * filter only to the picker dialog, not to drag-and-drop or a
 * programmatic `.files` assignment, so `applyAccept: false` is what
 * exercises the app's own (now-relaxed) handling rather than the test
 * harness's simulated picker.
 */
function selectFile(file: File) {
  const input = document.querySelector('input[type="file"]') as HTMLInputElement
  return userEvent.upload(input, file, { applyAccept: false })
}

describe('PhotoField', () => {
  it('uses the resolved URL as the avatar image source', () => {
    renderField('/api/v1/media/photos/abc.jpg')

    const image = document.querySelector('img')
    expect(image).toHaveAttribute('src', '/api/v1/media/photos/abc.jpg')
  })

  it('rejects an oversized file without making a request', async () => {
    const { toast } = await import('sonner')
    let requested = false
    server.use(
      http.put('/api/v1/me/profile/photo', () => {
        requested = true
        return HttpResponse.json({ photo_url: '/x', thumbnail_url: '/x' })
      }),
    )
    renderField()

    const oversized = new File([new Uint8Array(6 * 1024 * 1024)], 'big.jpg', {
      type: 'image/jpeg',
    })
    await selectFile(oversized)

    expect(toast.error).toHaveBeenCalledWith(expect.stringMatching(/5 mb/i))
    expect(requested).toBe(false)
  })

  it('still uploads a file whose type is empty', async () => {
    let requested = false
    server.use(
      http.put('/api/v1/me/profile/photo', () => {
        requested = true
        return HttpResponse.json({ photo_url: '/x', thumbnail_url: '/x' })
      }),
    )
    renderField()

    // The browser derives `type` from the extension; some OS/browser
    // combinations report it as empty rather than refusing the file, and
    // R-07 makes the server's decoded-bytes check the authority — the
    // client no longer hard-rejects on this (T177).
    const emptyTypeFile = new File([new Uint8Array(10)], 'photo.jpg', { type: '' })
    await selectFile(emptyTypeFile)

    await waitFor(() => expect(requested).toBe(true))
  })

  it('surfaces a 415 response naming the accepted formats and size limit', async () => {
    const { toast } = await import('sonner')
    server.use(
      http.put('/api/v1/me/profile/photo', () =>
        HttpResponse.json(
          {
            error: {
              code: 'unsupported_image',
              message: 'Upload a JPEG, PNG, or WebP image no larger than 5 MB.',
            },
          },
          { status: 415 },
        ),
      ),
    )
    renderField()

    const badFile = new File([new Uint8Array(10)], 'photo.gif', { type: 'image/gif' })
    await selectFile(badFile)

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(
        expect.stringMatching(/jpeg, png, or webp.*5 mb/i),
      ),
    )
  })
})
