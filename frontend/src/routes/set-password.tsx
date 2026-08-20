import { createFileRoute } from '@tanstack/react-router'
import { z } from 'zod'

import { SetPasswordPage } from '@/pages/set-password'

const setPasswordSearchSchema = z.object({
  token: z.string(),
})

export const Route = createFileRoute('/set-password')({
  validateSearch: setPasswordSearchSchema,
  component: SetPasswordPage,
})
