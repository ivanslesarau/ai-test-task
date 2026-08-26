import { describe, expect, it } from 'vitest'

import { ApiError } from '@/shared/api/errors'
import { fieldErrorText, toServerErrorMap } from '@/shared/lib/form-errors'

describe('fieldErrorText', () => {
  it('returns null when there are no errors', () => {
    expect(fieldErrorText([])).toBeNull()
  })

  it('reads the message off a Standard-Schema issue object', () => {
    expect(fieldErrorText([{ message: 'Required' }])).toBe('Required')
  })

  it('returns a string-valued error as-is', () => {
    expect(fieldErrorText(['Passwords do not match'])).toBe('Passwords do not match')
  })

  it('skips empty/falsy entries and returns the first renderable one', () => {
    expect(fieldErrorText([undefined, null, '', { message: 'Second' }])).toBe('Second')
  })
})

describe('toServerErrorMap', () => {
  it('maps ApiError.fields onto a field map with no form message', () => {
    const error = new ApiError(422, 'validation_failed', 'One or more fields are invalid.', [
      { field: 'phone', message: 'Enter a valid phone number.' },
    ])
    expect(toServerErrorMap(error)).toEqual({ fields: { phone: 'Enter a valid phone number.' } })
  })

  it('falls back to a form-level message when there are no field errors', () => {
    const error = new ApiError(409, 'conflict', 'An account with this email already exists.')
    expect(toServerErrorMap(error)).toEqual({
      form: 'An account with this email already exists.',
      fields: {},
    })
  })

  it('returns a generic form message for a non-ApiError', () => {
    expect(toServerErrorMap(new Error('boom'))).toEqual({
      form: 'An unexpected error occurred.',
      fields: {},
    })
  })
})
