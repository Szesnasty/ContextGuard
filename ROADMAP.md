# Roadmap

ContextGuard 1.0.0 is the first official MVP release: a library-first context
firewall, local demo stack, evidence viewer, policy DSL, deterministic
benchmark, and red-team corpus.

## Next Milestones

### 1. Expand Evaluations

- Grow the benchmark from demo-scale cases to 50-100 deterministic scenarios.
- Track false positives on benign corpora.
- Add bypass cases that are expected to fail today.
- Split reports by tenant isolation, role gating, PII, secrets, injection, and
  mixed-risk chunks.

### 2. Production-Style Policy Story

- Maintain both demo and strict policies.
- Add deny-by-default examples for enterprise RAG deployments.
- Document how source-system ACLs map into `UserContext` and chunk metadata.

### 3. Package And Integration Path

- Publish the Python library after the external package naming pass.
- Add small integration examples for common RAG frameworks.
- Keep the demo stack optional; the core should remain zero-infra.

### 4. Security Maturity

- Add private vulnerability reporting guidance.
- Harden identity beyond the dev-token stub.
- Define evidence retention and redaction expectations.
- Document deployment hardening assumptions.

### 5. Demo Polish

- Add a short recorded demo or GIF.
- Keep screenshots current with the dashboard.
- Add more identity-specific attack prompts.
