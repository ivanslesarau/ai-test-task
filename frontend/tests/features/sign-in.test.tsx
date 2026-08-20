import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { SignInForm } from '@/features/auth/sign-in/ui/sign-in-form'

import { server } from '../msw-server'

function renderForm(onSuccess: (user: unknown) => void) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <SignInForm onSuccess={onSuccess} />
    </QueryClientProvider>,
  )
}

describe('SignInForm', () => {
  it('shows validation errors for an empty submission', async () => {
    const onSuccess = vi.fn()
    renderForm(onSuccess)

    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByText(/email is required/i)).toBeInTheDocument()
    expect(onSuccess).not.toHaveBeenCalled()
  })

  it('rejects a malformed email before submitting', async () => {
    const onSuccess = vi.fn()
    renderForm(onSuccess)

    await userEvent.type(screen.getByLabelText(/email/i), 'not-an-email')
    await userEvent.type(screen.getByLabelText(/password/i), 'somepassword')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByText(/valid email/i)).toBeInTheDocument()
    expect(onSuccess).not.toHaveBeenCalled()
  })

  it('calls onSuccess with the signed-in user on valid submission', async () => {
    const onSuccess = vi.fn()
    renderForm(onSuccess)

    await userEvent.type(screen.getByLabelText(/email/i), 'admin@example.org')
    await userEvent.type(screen.getByLabelText(/password/i), 'correct-password-123456')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1))
    expect(onSuccess.mock.calls[0][0]).toMatchObject({ email: 'admin@example.org' })
  })

  it('renders the server error message on invalid credentials', async () => {
    server.use(
      http.post('/api/v1/auth/login', () =>
        HttpResponse.json(
          { error: { code: 'invalid_credentials', message: 'Email or password is incorrect.' } },
          { status: 401 },
        ),
      ),
    )
    const onSuccess = vi.fn()
    renderForm(onSuccess)

    await userEvent.type(screen.getByLabelText(/email/i), 'admin@example.org')
    await userEvent.type(screen.getByLabelText(/password/i), 'wrong-password-value')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByText(/email or password is incorrect/i)).toBeInTheDocument()
    expect(onSuccess).not.toHaveBeenCalled()
  })
})
