import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'

import { useUiStore } from '@/app/store/ui-store'
import { DeactivateDialog } from '@/features/admin/deactivate-user/ui/deactivate-dialog'

import { fixtures } from '../msw-handlers'
import { server } from '../msw-server'

function renderDialog() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <DeactivateDialog />
    </QueryClientProvider>,
  )
}

function openDeactivateDialog() {
  act(() => {
    useUiStore.getState().openPendingAction({ kind: 'deactivate', userId: fixtures.userDetail.id })
  })
}

describe('DeactivateDialog', () => {
  beforeEach(() => {
    act(() => {
      useUiStore.getState().clearPendingAction()
    })
  })

  it('is closed when there is no pending deactivate action', () => {
    renderDialog()
    expect(screen.queryByText(/deactivate this user/i)).not.toBeInTheDocument()
  })

  it('shows the stated consequences and requires confirmation', async () => {
    renderDialog()
    openDeactivateDialog()

    expect(await screen.findByText(/deactivate this user/i)).toBeInTheDocument()
    expect(screen.getByText(/will not be able to log in/i)).toBeInTheDocument()
    expect(screen.getByText(/historical data will be preserved/i)).toBeInTheDocument()
  })

  it('cancelling changes nothing and closes the dialog', async () => {
    let deactivateCalled = false
    server.use(
      http.post('/api/v1/admin/users/:userId/deactivate', () => {
        deactivateCalled = true
        return HttpResponse.json(fixtures.userDetail)
      }),
    )
    renderDialog()
    openDeactivateDialog()
    await screen.findByText(/deactivate this user/i)

    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))

    expect(deactivateCalled).toBe(false)
    await waitFor(() => expect(useUiStore.getState().pendingAction).toBeNull())
  })

  it('confirming calls the deactivate endpoint with the current version', async () => {
    let capturedUrl: string | null = null
    let capturedBody: unknown = null
    server.use(
      http.post('/api/v1/admin/users/:userId/deactivate', async ({ request }) => {
        capturedUrl = request.url
        capturedBody = await request.json()
        return HttpResponse.json({ ...fixtures.userDetail, status: 'inactive' })
      }),
    )
    renderDialog()
    openDeactivateDialog()
    await screen.findByText(/deactivate this user/i)
    // Ensure the account query behind the dialog has resolved before
    // interacting — the confirm handler reads its version from this data.
    await waitFor(() => expect(screen.getByRole('button', { name: /^deactivate$/i })).toBeEnabled())

    await userEvent.click(screen.getByRole('button', { name: /^deactivate$/i }))

    await waitFor(() => expect(capturedBody).toEqual({ version: fixtures.userDetail.version }))
    expect(capturedUrl).toContain(`/admin/users/${fixtures.userDetail.id}/deactivate`)
  })
})
