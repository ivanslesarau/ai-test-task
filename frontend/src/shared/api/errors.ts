import { AxiosError } from 'axios'

export interface FieldError {
  field: string
  message: string
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly fields: FieldError[]

  constructor(status: number, code: string, message: string, fields: FieldError[] = []) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.fields = fields
  }

  fieldMessage(field: string): string | undefined {
    return this.fields.find((f) => f.field === field)?.message
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}

interface ErrorEnvelopeBody {
  error: {
    code: string
    message: string
    fields?: FieldError[]
  }
}

function isErrorEnvelope(data: unknown): data is ErrorEnvelopeBody {
  if (typeof data !== 'object' || data === null || !('error' in data)) return false
  const err = (data as { error: unknown }).error
  return (
    typeof err === 'object' &&
    err !== null &&
    'code' in err &&
    'message' in err &&
    typeof (err as { code: unknown }).code === 'string' &&
    typeof (err as { message: unknown }).message === 'string'
  )
}

/** The one place `unknown` is narrowed for a failed request (constitution
 * Principle II: `unknown` plus a type guard, never `any`). */
export function toApiError(error: unknown): ApiError {
  if (error instanceof AxiosError) {
    const status = error.response?.status ?? 0
    const data: unknown = error.response?.data
    if (isErrorEnvelope(data)) {
      return new ApiError(status, data.error.code, data.error.message, data.error.fields ?? [])
    }
    return new ApiError(status, 'network_error', error.message)
  }
  if (error instanceof Error) {
    return new ApiError(0, 'unknown_error', error.message)
  }
  return new ApiError(0, 'unknown_error', 'An unexpected error occurred.')
}
