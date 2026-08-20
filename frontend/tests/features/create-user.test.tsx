import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { CreateUserForm } from '@/features/admin/create-user/ui/create-user-form'

import { server } from '../msw-server'

function renderForm(onSuccess: (result: unknown) => void) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <CreateUserForm onSuccess={onSuccess} />
    </QueryClientProvider>,
  )
}

async function selectRole(label: string) {
  await userEvent.click(screen.getByRole('combobox'))
  const listbox = await screen.findByRole('listbox')
  await userEvent.click(within(listbox).getByText(label))
}

describe('CreateUserForm', () => {
  it('requires a business name when the role is Trainer', async () => {
    const onSuccess = vi.fn()
    renderForm(onSuccess)

    await userEvent.type(screen.getByLabelText(/email/i), 'trainer@example.org')
    await userEvent.type(screen.getByLabelText(/first name/i), 'Tara')
    await userEvent.type(screen.getByLabelText(/last name/i), 'Trainer')
    await userEvent.type(screen.getByLabelText(/phone/i), '+15551234567')
    await userEvent.click(screen.getByRole('button', { name: /create user/i }))

    expect(await screen.findByText(/business name is required/i)).toBeInTheDocument()
    expect(onSuccess).not.toHaveBeenCalled()
  })

  it('does not show a business name field for a Coach', async () => {
    renderForm(vi.fn())

    await selectRole('Coach')

    expect(screen.queryByLabelText(/business name/i)).not.toBeInTheDocument()
  })

  it('submits successfully once all required fields are valid', async () => {
    const onSuccess = vi.fn()
    renderForm(onSuccess)

    await selectRole('Coach')
    await userEvent.type(screen.getByLabelText(/email/i), 'new-coach@example.org')
    await userEvent.type(screen.getByLabelText(/first name/i), 'Cody')
    await userEvent.type(screen.getByLabelText(/last name/i), 'Coach')
    await userEvent.type(screen.getByLabelText(/phone/i), '+15551234567')
    await userEvent.click(screen.getByRole('button', { name: /create user/i }))

    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1))
  })

  it('maps a 422 duplicate-email response onto a visible error', async () => {
    server.use(
      http.post('/api/v1/admin/users', () =>
        HttpResponse.json(
          {
            error: {
              code: 'email_already_registered',
              message: 'An account with this email address already exists.',
            },
          },
          { status: 409 },
        ),
      ),
    )
    const onSuccess = vi.fn()
    renderForm(onSuccess)

    await selectRole('Coach')
    await userEvent.type(screen.getByLabelText(/email/i), 'dup@example.org')
    await userEvent.type(screen.getByLabelText(/first name/i), 'Cody')
    await userEvent.type(screen.getByLabelText(/last name/i), 'Coach')
    await userEvent.type(screen.getByLabelText(/phone/i), '+15551234567')
    await userEvent.click(screen.getByRole('button', { name: /create user/i }))

    expect(await screen.findByText(/already exists/i)).toBeInTheDocument()
    expect(onSuccess).not.toHaveBeenCalled()
  })
})
