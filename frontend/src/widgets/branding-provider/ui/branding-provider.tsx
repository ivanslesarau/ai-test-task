import type { CSSProperties, ReactNode } from 'react'

import { brandPalette } from '@/shared/lib/brand-palette'
import type { PortalBranding } from '@/shared/api/types'

interface BrandingProviderProps {
  branding: PortalBranding | undefined
  children: ReactNode
}

/**
 * Sets the runtime-overridable `--brand-primary*` custom properties
 * `app/styles/globals.css` declares, from one resolved `PortalBranding`
 * value. Mounted at `routes/_authed.tsx` (from the session) and at
 * `routes/join.$code.tsx` (from the join preview) — never at `__root`,
 * so `/login` and `/set-password` keep the platform default
 * (constitution: design tokens; FR-101).
 *
 * No component below this one reads `primary_color` or holds a hex
 * literal — every consumer uses the `bg-brand-primary` family of
 * Tailwind utilities, which resolve through these variables.
 */
export function BrandingProvider({ branding, children }: BrandingProviderProps) {
  if (!branding?.primary_color) {
    // Platform default: no inline style override, so the @theme
    // block's own :root values apply.
    return <>{children}</>
  }

  const palette = brandPalette(branding.primary_color)
  const style = Object.fromEntries(Object.entries(palette)) as CSSProperties

  return (
    <div style={style} className="contents">
      {children}
    </div>
  )
}
