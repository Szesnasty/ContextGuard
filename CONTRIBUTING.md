# Contributing

Thanks for taking ContextGuard seriously. The project is intentionally narrow:
control which retrieved chunks may reach the model, redact sensitive context,
and record evidence for every decision.

## Local Setup

```bash
make install
make ci
```

Run the local demo:

```bash
make demo
```

Optional local configuration:

```bash
cp .env.example .env
```

## Development Rules

- Keep the zero-infra core lightweight: no framework, database, model, or network
  dependency in `contextguard.core`.
- Treat identity as trusted only after token verification. Do not accept identity
  from request bodies.
- Keep policy decisions deterministic and explainable.
- Add or update tests for new policy behavior, redaction behavior, evidence
  fields, or demo scenarios.
- Do not commit real secrets, private documents, customer data, personal data, or
  local `.env` files.
- Keep examples in English and use synthetic data only.

## Useful Commands

```bash
make test
make lint
make types
make build
make benchmark
make red-team
make e2e
```

## Pull Request Checklist

- The change has a focused scope.
- `make ci` passes locally, or the PR explains why it was not run.
- New policy or redaction behavior has tests.
- Public documentation stays honest about limitations.
- No real sensitive data is included in fixtures, screenshots, logs, or docs.
