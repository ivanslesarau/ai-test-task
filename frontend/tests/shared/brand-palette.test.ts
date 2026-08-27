import { describe, expect, it } from 'vitest'

import { brandPalette, contrastRatio } from '@/shared/lib/brand-palette'

function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace('#', '')
  return [
    parseInt(clean.slice(0, 2), 16),
    parseInt(clean.slice(2, 4), 16),
    parseInt(clean.slice(4, 6), 16),
  ]
}

/** Every text-bearing surface a trainer's colour can produce must clear
 * WCAG 4.5:1 against its own foreground — this test IS SC-023. Swept
 * across the hue wheel, including the mid-tone lightness band where
 * neither pure black nor pure white text reaches 4.5:1 against the raw
 * colour, which is exactly the case the surface-adjustment exists for. */
describe('brandPalette — SC-023 contrast sweep', () => {
  const hues = Array.from({ length: 36 }, (_, i) => i * 10)
  const saturations = [20, 50, 80, 100]
  const lightnesses = [10, 25, 40, 50, 55, 60, 65, 75, 90]

  function hslToHex(h: number, s: number, l: number): string {
    const sn = s / 100
    const ln = l / 100
    const c = (1 - Math.abs(2 * ln - 1)) * sn
    const x = c * (1 - Math.abs(((h / 60) % 2) - 1))
    const m = ln - c / 2
    let [rp, gp, bp] = [0, 0, 0]
    if (h < 60) [rp, gp, bp] = [c, x, 0]
    else if (h < 120) [rp, gp, bp] = [x, c, 0]
    else if (h < 180) [rp, gp, bp] = [0, c, x]
    else if (h < 240) [rp, gp, bp] = [0, x, c]
    else if (h < 300) [rp, gp, bp] = [x, 0, c]
    else [rp, gp, bp] = [c, 0, x]
    const toHex = (v: number) =>
      Math.round((v + m) * 255)
        .toString(16)
        .padStart(2, '0')
    return `#${toHex(rp)}${toHex(gp)}${toHex(bp)}`
  }

  for (const h of hues) {
    for (const s of saturations) {
      for (const l of lightnesses) {
        const hex = hslToHex(h, s, l)
        it(`clears 4.5:1 for hsl(${h}, ${s}%, ${l}%) = ${hex}`, () => {
          const palette = brandPalette(hex)
          const surfaceRgb = hexToRgb(palette['--brand-surface'])
          const onSurfaceRgb = hexToRgb(palette['--brand-on-surface'])
          expect(contrastRatio(surfaceRgb, onSurfaceRgb)).toBeGreaterThanOrEqual(4.5)
        })
      }
    }
  }

  it('leaves --brand-primary exactly as chosen, unmodified', () => {
    const palette = brandPalette('#3366cc')
    expect(palette['--brand-primary']).toBe('#3366cc')
  })

  it('derives soft/deep by ±20 HSL lightness points and rgb as a comma triple', () => {
    const palette = brandPalette('#3366cc')
    expect(palette['--brand-primary-soft']).not.toBe('#3366cc')
    expect(palette['--brand-primary-deep']).not.toBe('#3366cc')
    expect(palette['--brand-primary-rgb']).toBe('51, 102, 204')
  })

  it('does not adjust the surface when the raw colour already clears 4.5:1', () => {
    // Near-black already contrasts >4.5:1 against white text.
    const palette = brandPalette('#0a0a0a')
    expect(palette['--brand-surface']).toBe('#0a0a0a')
    expect(palette['--brand-on-surface']).toBe('#ffffff')
  })

  it('picks black text against a light colour and white text against a dark one', () => {
    expect(brandPalette('#fefefe')['--brand-on-surface']).toBe('#000000')
    expect(brandPalette('#010101')['--brand-on-surface']).toBe('#ffffff')
  })

  it('is a pure function — same input, same output', () => {
    expect(brandPalette('#7788cc')).toEqual(brandPalette('#7788cc'))
  })
})
