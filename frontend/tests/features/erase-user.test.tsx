import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'

import { useUiStore } from '@/app/store/ui-store'
import { EraseDialog } from '@/features/admin/erase-user/ui/erase-dialog'

import { fixtures } from '../msw-handlers'
import { server } from '../msw-server'

function renderDialog() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <EraseDialog />
    </QueryClientProvider>,
  )
}

function openEraseDialog() {
  act(() => {
    useUiStore.getState().openPendingAction({ kind: 'erase', userId: fixtures.userDetail.id })
  })
}

describe('EraseDialog', () => {
  beforeEach(() => {
    act(() => {
      useUiStore.getState().clearPendingAction()
    })
  })

  it('shows the irreversible-action warning', async () => {
    renderDialog()
    openEraseDialog()

    expect(await screen.findByText(/erase this user/i)).toBeInTheDocument()
    expect(screen.getByText(/personal information will be removed/i)).toBeInTheDocument()
    expect(screen.getByText(/cannot be undone/i)).toBeInTheDocument()
  })

  it('confirmation is disabled until a reason is entered', async () => {
    renderDialog()
    openEraseDialog()
    await screen.findByText(/erase this user/i)

    const confirmButton = screen.getByRole('button', { name: /^erase$/i })
    expect(confirmButton).toBeDisabled()

    await userEvent.type(screen.getByLabelText(/reason/i), 'GDPR request')

    expect(confirmButton).toBeEnabled()
  })

  it('submits the entered reason', async () => {
    let capturedBody: unknown = null
    server.use(
      http.post('/api/v1/admin/users/:userId/erase', async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json({ ...fixtures.userDetail, status: 'deleted' })
      }),
    )
    renderDialog()
    openEraseDialog()
    await screen.findByText(/erase this user/i)

    await userEvent.type(screen.getByLabelText(/reason/i), 'GDPR request')
    await userEvent.click(screen.getByRole('button', { name: /^erase$/i }))

    await waitFor(() =>
      expect(capturedBody).toEqual({ version: fixtures.userDetail.version, reason: 'GDPR request' }),
    )
  })
})
