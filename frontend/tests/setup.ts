import '@testing-library/jest-dom/vitest'
import { afterAll, afterEach, beforeAll } from 'vitest'

import { apiClient } from '@/shared/api/client'
import { registerInterceptors } from '@/shared/api/interceptors'

import { server } from './msw-server'

// Mirrors the one-time registration main.tsx does for the real app — without
// this, component tests see raw AxiosErrors instead of the ApiError shape
// every feature is written against.
registerInterceptors(apiClient, () => {})

// jsdom doesn't implement scrollTo; TanStack Router's scroll restoration
// calls it on every navigation during tests.
window.scrollTo = () => {}

// jsdom doesn't implement the Pointer Capture API that Radix UI's Select
// (and other primitives) rely on for pointer-driven interactions.
Element.prototype.hasPointerCapture = () => false
Element.prototype.setPointerCapture = () => {}
Element.prototype.releasePointerCapture = () => {}
Element.prototype.scrollIntoView = () => {}

// jsdom doesn't implement ResizeObserver, which several Radix UI
// primitives (Checkbox, Select) use to measure themselves.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver

// jsdom doesn't implement createObjectURL/revokeObjectURL, which
// BrandingForm uses for a local logo preview before the file is saved
// (FR-097).
URL.createObjectURL = () => 'blob:mock-object-url'
URL.revokeObjectURL = () => {}

// jsdom doesn't implement matchMedia, which sonner's <Toaster/> reads to
// pick a light/dark theme on mount (US12, tasks.md T411 — the first test
// suite to render Toaster alongside a page, for its decision-outcome
// toasts).
window.matchMedia =
  window.matchMedia ||
  (((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
