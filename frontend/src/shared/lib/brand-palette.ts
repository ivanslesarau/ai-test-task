/**
 * Pure derivation from a trainer's chosen brand colour to a palette of CSS
 * custom property values (constitution: styling MUST use design tokens
 * through CSS custom properties — no component holds a hex literal, and
 * this is the only place the trainer's raw colour is read; research.md
 * R-29).
 *
 * `--brand-primary`, `--brand-primary-soft`, `--brand-primary-deep`, and
 * `--brand-primary-rgb` are exactly Task/designs/DESIGN_TOKENS.md's
 * "Dynamic Color Generation" formula — lighten/darken the chosen colour by
 * 20 percentage points of HSL lightness, plus an RGB triple for `rgba()`
 * usage — and match the runtime-overridable `:root` variables
 * `app/styles/globals.css` already declares for exactly this purpose.
 * `--brand-primary` is never mutated from what the trainer chose.
 *
 * Those four are for accents, borders, and gradients, where legibility
 * does not apply. Anywhere text sits directly on a brand-coloured surface
 * (a "Join {trainer}" button, for instance) must use `--brand-surface` /
 * `--brand-on-surface` instead — a pair the design tokens don't name, added
 * here because DESIGN_TOKENS.md's fixed ±20-point shift has no guarantee
 * of clearing WCAG's 4.5:1 ratio (SC-023, FR-099), and a narrow mid-tone
 * band exists where neither pure black nor white text does either against
 * the raw colour. `--brand-surface` walks away from the raw colour only as
 * far as contrast requires; it equals `--brand-primary` whenever the raw
 * colour already clears the bar on its own.
 */

export interface BrandPalette {
  '--brand-primary': string
  '--brand-primary-soft': string
  '--brand-primary-deep': string
  '--brand-primary-rgb': string
  '--brand-surface': string
  '--brand-on-surface': string
}

type Rgb = readonly [number, number, number]

const BLACK: Rgb = [0, 0, 0]
const WHITE: Rgb = [255, 255, 255]
const MIN_CONTRAST = 4.5

function hexToRgb(hex: string): Rgb {
  const clean = hex.replace('#', '')
  const r = parseInt(clean.slice(0, 2), 16)
  const g = parseInt(clean.slice(2, 4), 16)
  const b = parseInt(clean.slice(4, 6), 16)
  return [r, g, b]
}

function rgbToHex([r, g, b]: Rgb): string {
  const toHex = (n: number) =>
    Math.round(Math.min(255, Math.max(0, n)))
      .toString(16)
      .padStart(2, '0')
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`
}

function relativeLuminance([r, g, b]: Rgb): number {
  const [rl, gl, bl] = [r, g, b].map((channel) => {
    const c = channel / 255
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
  }) as [number, number, number]
  return 0.2126 * rl + 0.7152 * gl + 0.0722 * bl
}

/** WCAG 2.2 contrast ratio, 1:1 (identical) to 21:1 (black on white). */
export function contrastRatio(a: Rgb, b: Rgb): number {
  const la = relativeLuminance(a)
  const lb = relativeLuminance(b)
  const lighter = Math.max(la, lb)
  const darker = Math.min(la, lb)
  return (lighter + 0.05) / (darker + 0.05)
}

function rgbToHsl([r, g, b]: Rgb): [number, number, number] {
  const rn = r / 255
  const gn = g / 255
  const bn = b / 255
  const max = Math.max(rn, gn, bn)
  const min = Math.min(rn, gn, bn)
  const l = (max + min) / 2
  const delta = max - min

  if (delta === 0) return [0, 0, l * 100]

  const s = delta / (1 - Math.abs(2 * l - 1))
  let h: number
  if (max === rn) h = ((gn - bn) / delta) % 6
  else if (max === gn) h = (bn - rn) / delta + 2
  else h = (rn - gn) / delta + 4
  h *= 60
  if (h < 0) h += 360

  return [h, s * 100, l * 100]
}

function hslToRgb([h, s, l]: [number, number, number]): Rgb {
  const sn = s / 100
  const ln = l / 100
  const c = (1 - Math.abs(2 * ln - 1)) * sn
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1))
  const m = ln - c / 2

  let rp = 0
  let gp = 0
  let bp = 0
  if (h < 60) [rp, gp, bp] = [c, x, 0]
  else if (h < 120) [rp, gp, bp] = [x, c, 0]
  else if (h < 180) [rp, gp, bp] = [0, c, x]
  else if (h < 240) [rp, gp, bp] = [0, x, c]
  else if (h < 300) [rp, gp, bp] = [x, 0, c]
  else [rp, gp, bp] = [c, 0, x]

  return [(rp + m) * 255, (gp + m) * 255, (bp + m) * 255]
}

const LIGHTEN_DARKEN_POINTS = 20

function shiftLightness(rgb: Rgb, deltaPoints: number): string {
  const [h, s, l] = rgbToHsl(rgb)
  return rgbToHex(hslToRgb([h, s, Math.min(100, Math.max(0, l + deltaPoints))]))
}

/** The best of black/white against `rgb`, walked toward the matching
 * extreme only as far as needed to clear 4.5:1 — never further than the
 * raw colour requires, and never applied to `--brand-primary` itself. */
function safeSurfaceAndForeground(rgb: Rgb): { surface: Rgb; foreground: Rgb } {
  const contrastWithBlack = contrastRatio(rgb, BLACK)
  const contrastWithWhite = contrastRatio(rgb, WHITE)
  const foreground: Rgb = contrastWithWhite >= contrastWithBlack ? WHITE : BLACK

  if (contrastRatio(rgb, foreground) >= MIN_CONTRAST) {
    return { surface: rgb, foreground }
  }

  // White text needs a darker surface; black text needs a lighter one.
  // Walking toward the matching extreme is guaranteed to cross 4.5:1
  // before (or exactly at) that extreme, since pure black/white against
  // its opposite is ~21:1.
  const [h, s, startL] = rgbToHsl(rgb)
  const step = foreground === WHITE ? -1 : 1
  let l = startL
  let surface: Rgb = rgb

  for (let i = 0; i < 100; i++) {
    l = Math.min(100, Math.max(0, l + step))
    surface = hslToRgb([h, s, l])
    if (contrastRatio(surface, foreground) >= MIN_CONTRAST) break
    if (l === 0 || l === 100) break
  }

  return { surface, foreground }
}

/**
 * Derives the full palette for one trainer's chosen colour. Pure and
 * synchronous — safe to call on every render. `frontend/tests/shared/
 * brand-palette.test.ts` sweeps the colour space to prove `--brand-surface`
 * / `--brand-on-surface` clear 4.5:1 everywhere (SC-023).
 */
export function brandPalette(primaryHex: string): BrandPalette {
  const primaryRgb = hexToRgb(primaryHex)
  const { surface, foreground } = safeSurfaceAndForeground(primaryRgb)

  return {
    '--brand-primary': primaryHex,
    '--brand-primary-soft': shiftLightness(primaryRgb, LIGHTEN_DARKEN_POINTS),
    '--brand-primary-deep': shiftLightness(primaryRgb, -LIGHTEN_DARKEN_POINTS),
    '--brand-primary-rgb': primaryRgb.join(', '),
    '--brand-surface': rgbToHex(surface),
    '--brand-on-surface': rgbToHex(foreground),
  }
}
