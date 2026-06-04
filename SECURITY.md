# Security Policy

ContextGuard is a security-oriented demo and library for policy-aware RAG context
control. It is not a compliance certification or a production security review.

## Supported Versions

| Version | Supported |
|---|---|
| 1.0.x | Yes |

## Reporting A Vulnerability

Please report suspected vulnerabilities privately through GitHub's private
vulnerability reporting flow when available, or by opening a minimal issue that
does not include exploit details or sensitive data.

Include:

- the affected component,
- the expected policy outcome,
- the observed policy outcome,
- a minimal reproduction,
- whether sensitive context reached the model, API response, evidence record, or
  logs.

Do not include real secrets, customer data, access tokens, private documents, or
production logs in a public issue.

## Scope

In scope:

- policy bypasses that allow blocked chunks to reach the prompt,
- redaction failures for detected PII or secret spans,
- tenant or role isolation mistakes,
- evidence records that expose withheld raw text where they should not,
- prompt-injection cases that the committed policy claims to block.

Out of scope:

- vulnerabilities in local demo dependencies,
- production deployment hardening,
- identity provider integration,
- connector-level ACL synchronization,
- compliance or legal guarantees.

## Current Security Model

ContextGuard enforces policy at the context boundary between retrieval and
generation. The current demo uses signed dev tokens, planted demo corpora, local
Ollama models, and deterministic policy rules. Production use still requires
hardened identity, connector-level ACL mapping, retention controls, deployment
hardening, logging review, and a full security assessment.
