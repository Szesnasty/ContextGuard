# ContextGuard Web

Vue dashboard for the ContextGuard demo stack.

This app is the operator-facing proof surface for ContextGuard: it lets you run
RAG queries under a selected identity, inspect which retrieved sources were
allowed, redacted, or withheld, and review the policy evidence behind each
decision.

It is intentionally not a marketing site. The first screen is the working demo:
a RAG console with identity-aware retrieval, one-click model presets, planted
attack prompts, and source-level evidence.

## What It Shows

- **RAG Console** - ask questions against the demo corpus and see the model
  answer together with allowed, redacted, and blocked source counts.
- **Documents & attacks drawer** - browse planted documents and load
  role-specific attack prompts into the chat.
- **Sources & evidence drawer** - inspect every retrieved document, the guarded
  chunks, and the policy rule that allowed, redacted, or withheld each one.
- **Evidence Viewer** - replay previous runs, compare context before and after
  the firewall, and see the decision flow.
- **Policy Editor** - edit the policy YAML with live validation against the
  committed schema.

## Local Demo

From the repository root:

```bash
make demo
```

The demo command starts the API, local services, seeded corpus, and this
dashboard. It prints the dashboard URL when ready. The default Vite port is
`5173`, but the demo runner may choose the next available port if something is
already listening there.

For frontend-only development:

```bash
pnpm --filter @contextguard/web dev
```

By default the Vite dev server proxies `/v1`, `/health`, and `/metrics` to the
local API at `http://localhost:8000`. To point the proxy at a different API:

```bash
VITE_API_PROXY=http://127.0.0.1:8008 pnpm --filter @contextguard/web dev
```

For a deployed or non-proxied frontend, set `VITE_API_BASE` to the absolute API
origin.

## Demo Script

A strong first walkthrough:

1. Select `sales@acme`.
2. Open **Documents & attacks**.
3. Load the M&A acquisition prompt.
4. Send the query.
5. Open **View sources** and show that the confidential source was retrieved but
   withheld from the model.
6. Switch to an allowed role and re-run the same prompt to show that the
   decision changes with identity, not with keyword censorship.
7. Load the prompt-injection attack and show that the poisoned document is
   blocked before prompt assembly.

The core invariant to demonstrate:

```text
blocked chunk text does not reach the model
```

## Commands

```bash
pnpm --filter @contextguard/web dev
pnpm --filter @contextguard/web test
pnpm --filter @contextguard/web lint
pnpm --filter @contextguard/web typecheck
pnpm --filter @contextguard/web build
```

Root-level CI runs these through `make lint`, `make types`, `make test`, and
`make build`.

## Implementation Notes

- API types are generated from the committed OpenAPI snapshot in
  `packages/contracts/ts/openapi.json`.
- Markdown and diagram rendering go through dedicated components instead of raw
  template HTML.
- Reports copied into `public/reports/` are generated from the repository-root
  red-team and benchmark reports during `predev` and `prebuild`.
- The dashboard is demo-focused. It is not an admin console, production auth
  surface, or hosted SaaS frontend yet.

