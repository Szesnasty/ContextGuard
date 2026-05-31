---
applyTo: "apps/web/**/*.{vue,ts}"
---

# Vue SFC rules (ContextGuard web)

These are mandatory for every `.vue` component and its supporting `.ts` in
`apps/web`. They exist to keep views thin, logic testable, and styling consistent.

## 1. Logic lives in a composable, never in the view

- Every view/component delegates **all logic to a composable** (`src/composables/useX.ts`).
- The `<script setup>` only: declares `props`/`emits`, calls the composable, and
  exposes its result to the template. No business logic, no API calls, no data
  shaping in the SFC.
- One composable per view/feature. Name it `useThing()` and return a typed object.
- Composables are the unit under test (Vitest), not the SFC.

## 2. Early return pattern

- Use guard clauses; handle the invalid/edge case first and `return` early.
- No deep nesting, no `else` after a `return`.

```ts
function run() {
  if (!isAuthenticated.value) return setError("no token");
  if (!query.value.trim()) return setError("empty query");
  // happy path, un-nested
}
```

## 3. Self-descriptive names

- Variables and functions say what they are: `retrievedChunks`, `guardedContext`,
  `isRunning`. No `d`, `x`, `tmp`, `data2`.
- Booleans read as predicates: `isAuthenticated`, `hasMismatch`, `canSubmit`.

## 4. Styling: SCSS + BEM only

- Each component uses `<style scoped lang="scss">`.
- Class names follow **BEM**: `.block`, `.block__element`, `.block--modifier`.
- **No inline `style="..."`** and no utility-class soup in templates.
- Shared design tokens (colors, spacing, radii) come from SCSS variables via
  `@use "@/styles/tokens" as *;` — never hard-code hex in components.

## 5. Declaration order (always identical)

Inside composables (and any `<script setup>` that holds state), declare in this
fixed order:

1. `ref` / reactive state
2. `computed`
3. `watch` / `watchEffect`
4. functions (handlers and the ones returned/exported last)

The composable's `return { ... }` is the public surface and comes at the end.
