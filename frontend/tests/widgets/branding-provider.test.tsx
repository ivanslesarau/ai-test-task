import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { BrandingProvider } from '@/widgets/branding-provider/ui/branding-provider'

const BRANDED = { logo_url: '/media/branding/x.png', primary_color: '#3366cc', updated_at: null }
const DEFAULT_BRANDING = { logo_url: null, primary_color: null, updated_at: null }

describe('BrandingProvider', () => {
  it('sets the --brand-primary custom properties when a colour is present', () => {
    render(
      <BrandingProvider branding={BRANDED}>
        <span data-testid="child">child</span>
      </BrandingProvider>,
    )

    const wrapper = screen.getByTestId('child').parentElement as HTMLElement
    expect(wrapper.style.getPropertyValue('--brand-primary')).toBe('#3366cc')
    expect(wrapper.style.getPropertyValue('--brand-primary-soft')).not.toBe('')
    expect(wrapper.style.getPropertyValue('--brand-primary-deep')).not.toBe('')
    expect(wrapper.style.getPropertyValue('--brand-primary-rgb')).toBe('51, 102, 204')
  })

  it('falls back to the platform default when no colour is set — no inline override', () => {
    render(
      <BrandingProvider branding={DEFAULT_BRANDING}>
        <span data-testid="child">child</span>
      </BrandingProvider>,
    )

    const child = screen.getByTestId('child')
    // No wrapper div is introduced when there is nothing to override —
    // the child renders as a direct fragment child.
    expect(child.parentElement?.style.getPropertyValue('--brand-primary')).toBeFalsy()
  })

  it('falls back to the platform default when branding is undefined (still loading)', () => {
    render(
      <BrandingProvider branding={undefined}>
        <span data-testid="child">child</span>
      </BrandingProvider>,
    )

    expect(screen.getByTestId('child')).toBeInTheDocument()
  })
})
