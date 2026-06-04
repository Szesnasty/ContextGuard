# Changelog

## 1.0.0 - 2026-06-04

First official MVP release of ContextGuard.

### Added

- Zero-infra Python core for per-chunk allow, redact, and block decisions.
- Policy DSL with tenant isolation, role gating, classification gates, PII
  redaction, secret redaction, and prompt-injection blocking examples.
- FastAPI adapter with signed demo-token identity.
- Local RAG demo stack with pgvector, Redis, Ollama, Langfuse, and Vue dashboard.
- Evidence viewer showing decision flow, context delta, and enforced policy
  decisions.
- Deterministic benchmark and red-team reports.
- GitHub CI for lockfile verification, lint, typecheck, tests, and build.
- Apache-2.0 license, security policy, contribution guide, roadmap, screenshots,
  and local `.env.example` templates.

### Known Limitations

- Not a compliance certification or production deployment template.
- Public Python package publication is still planned after the external package
  naming and distribution pass.
- Production use still needs hardened identity, connector-level ACL mapping,
  retention policy, deployment hardening, and a full security review.
