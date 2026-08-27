import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { BrandingForm } from '@/features/trainer/branding/ui/branding-form'

import { server } from '../msw-server'

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}))

beforeEach(() => {
  vi.clearAllMocks()
  server.use(
    http.get('/api/v1/me/branding', () =>
      HttpResponse.json({ logo_url: null, primary_color: null, updated_at: null }),
    ),
  )
})

function renderForm() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <BrandingForm />
    </QueryClientProvider>,
  )
}

describe('BrandingForm — FR-097: nothing applies until Save', () => {
  it('does not call the upload endpoint when a file is merely chosen', async () => {
    let uploadCalled = false
    server.use(
      http.put('/api/v1/me/branding/logo', () => {
        uploadCalled = true
        return HttpResponse.json({ logo_url: '/media/branding/x.png', primary_color: null, updated_at: null })
      }),
    )
    renderForm()

    const fileInput = await screen.findByLabelText(/logo/i)
    const file = new File(['fake-png-bytes'], 'logo.png', { type: 'image/png' })
    await userEvent.upload(fileInput, file)

    // The file is chosen and previewed (an <img> now renders it), but no
    // network call has been made yet.
    expect(await screen.findByAltText(/logo preview/i)).toBeInTheDocument()
    expect(uploadCalled).toBe(false)
  })

  it('does not call the update-colour endpoint when a colour is merely picked', async () => {
    let updateCalled = false
    server.use(
      http.patch('/api/v1/me/branding', () => {
        updateCalled = true
        return HttpResponse.json({ logo_url: null, primary_color: '#336699', updated_at: null })
      }),
    )
    renderForm()

    const colorInput = await screen.findByLabelText(/primary colour/i)
    await userEvent.click(colorInput)
    // fireEvent used because userEvent has no dedicated color-input helper.
    const { fireEvent } = await import('@testing-library/react')
    fireEvent.change(colorInput, { target: { value: '#336699' } })

    expect(updateCalled).toBe(false)
  })

  it('saves both the file and the colour together when Save is pressed', async () => {
    let uploadCalled = false
    let savedColor: string | null = null
    server.use(
      http.put('/api/v1/me/branding/logo', () => {
        uploadCalled = true
        return HttpResponse.json({ logo_url: '/media/branding/x.png', primary_color: null, updated_at: null })
      }),
      http.patch('/api/v1/me/branding', async ({ request }) => {
        const body = (await request.json()) as { primary_color: string }
        savedColor = body.primary_color
        return HttpResponse.json({ logo_url: null, primary_color: body.primary_color, updated_at: null })
      }),
    )
    renderForm()

    const fileInput = await screen.findByLabelText(/logo/i)
    await userEvent.upload(fileInput, new File(['x'], 'logo.png', { type: 'image/png' }))

    const colorInput = await screen.findByLabelText(/primary colour/i)
    const { fireEvent } = await import('@testing-library/react')
    fireEvent.change(colorInput, { target: { value: '#336699' } })

    const saveButton = await screen.findByRole('button', { name: /save changes/i })
    await waitFor(() => expect(saveButton).toBeEnabled())
    await userEvent.click(saveButton)

    await waitFor(() => expect(uploadCalled).toBe(true))
    await waitFor(() => expect(savedColor).toBe('#336699'))
  })

  it('disables Save when nothing has changed', async () => {
    renderForm()

    const saveButton = await screen.findByRole('button', { name: /save changes/i })
    expect(saveButton).toBeDisabled()
  })
})
