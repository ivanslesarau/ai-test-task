import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ReinviteButton } from '@/features/admin/reinvite-user/ui/reinvite-button'

import { server } from '../msw-server'

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}))

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  vi.clearAllMocks()
})

function renderButton() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ReinviteButton userId="user-1" />
    </QueryClientProvider>,
  )
}

describe('ReinviteButton', () => {
  it('reports success when invitation_sent is true', async () => {
    const { toast } = await import('sonner')
    server.use(
      http.post('/api/v1/admin/users/user-1/reinvite', () =>
        HttpResponse.json({ invitation_sent: true, expires_at: '2026-01-02T00:00:00Z' }),
      ),
    )
    renderButton()

    await userEvent.click(screen.getByRole('button', { name: /re-invite/i }))

    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith('Invitation re-sent'))
    expect(toast.error).not.toHaveBeenCalled()
  })

  it('reports failure when invitation_sent is false, rather than reading it as success', async () => {
    const { toast } = await import('sonner')
    server.use(
      http.post('/api/v1/admin/users/user-1/reinvite', () =>
        HttpResponse.json({ invitation_sent: false, expires_at: '2026-01-02T00:00:00Z' }),
      ),
    )
    renderButton()

    await userEvent.click(screen.getByRole('button', { name: /re-invite/i }))

    await vi.waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(expect.stringMatching(/could not be sent/i)),
    )
    expect(toast.success).not.toHaveBeenCalled()
  })
})
