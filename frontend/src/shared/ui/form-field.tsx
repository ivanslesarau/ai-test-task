import * as React from 'react'

import { cn } from '@/shared/lib/utils'
import { Label } from '@/shared/ui/label'

/**
 * Presentational field wrappers, deliberately independent of any form
 * library. The constitution mandates TanStack Form, not react-hook-form,
 * so shadcn's stock `form.tsx` (which couples FormField/useFormField to
 * react-hook-form's Controller) was not used — these compose with a
 * TanStack Form `field.state` directly instead.
 */

function FormItem({ className, ...props }: React.ComponentProps<'div'>) {
  return <div data-slot="form-item" className={cn('grid gap-2', className)} {...props} />
}

function FormLabel({
  className,
  htmlFor,
  ...props
}: React.ComponentProps<typeof Label>) {
  return (
    <Label
      data-slot="form-label"
      htmlFor={htmlFor}
      className={cn('data-[error=true]:text-destructive', className)}
      {...props}
    />
  )
}

function FormMessage({
  className,
  children,
  ...props
}: React.ComponentProps<'p'>) {
  if (!children) return null
  return (
    <p
      data-slot="form-message"
      className={cn('text-destructive text-sm', className)}
      {...props}
    >
      {children}
    </p>
  )
}

function FormDescription({ className, ...props }: React.ComponentProps<'p'>) {
  return (
    <p
      data-slot="form-description"
      className={cn('text-muted-foreground text-sm', className)}
      {...props}
    />
  )
}

export { FormItem, FormLabel, FormMessage, FormDescription }
