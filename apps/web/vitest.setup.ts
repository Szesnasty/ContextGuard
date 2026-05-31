// Vitest global setup: stub browser APIs that jsdom lacks but our components
// (mermaid, monaco) probe at import time. Keeps unit tests headless and fast.
import { vi } from "vitest";

// Monaco and mermaid call matchMedia / ResizeObserver on init; jsdom has neither.
if (!window.matchMedia) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}

if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
