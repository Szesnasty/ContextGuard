# ContextGuard

> **An evidence layer for RAG systems.**
> ContextGuard enforces access policies, minimizes sensitive context, and produces an audit-ready record explaining why specific data was — or was not — sent to the model.

Most RAG systems answer: *"Did we retrieve relevant context?"*
ContextGuard answers: **"Were we allowed to retrieve this context — and can we prove it?"**

---

## The problem

Companies are deploying RAG and AI agents on top of their internal data — contracts, tickets, HR files, customer records, source code. The retrieval layer is usually built for **relevance**, not for **control**. That creates four blind spots that show up the moment a real auditor, DPO, or security lead starts asking questions:

1. **No access boundary inside the prompt.**
   The vector store happily returns the most semantically similar chunks, regardless of who is asking. A sales user can end up with finance chunks in their context window. Tenants can bleed into each other. Row-level permissions from the source system are not enforced at retrieval time.

2. **No data minimization at the prompt boundary.**
   GDPR-style minimization is usually applied to databases and exports, not to the context window. Models routinely receive 10–20× more text than the answer actually requires — including PII, secrets, and confidential clauses that were never needed to answer the question.

3. **No explainable decision trail.**
   When something leaks, teams cannot reconstruct *what was retrieved, what was sent, what was blocked, and why.* There is no per-query evidence record that a security or compliance reviewer can read.

4. **No resilience story.**
   Prompt injection, indirect injection via poisoned documents, and cross-tenant exfiltration attempts are not systematically tested. There is no artifact that says "we ran these adversarial scenarios, here is how the system behaved."

These are not theoretical risks. They are the first questions a serious enterprise buyer, internal security review, or EU regulator will ask about any RAG deployment.

## What ContextGuard is

ContextGuard sits **between your retriever and your model** as a policy-aware context firewall and evidence layer. For every query, it:

- **Enforces policy at retrieval time** — user role, tenant, document classification, and source-system permissions are applied *before* top-k selection, not after.
- **Minimizes the context window** — strips, redacts, or drops chunks that are not necessary to answer the question, and reports tokens-before vs. tokens-after.
- **Detects sensitive payloads** — PII, secrets, credentials, and classification labels are flagged and handled per policy.
- **Scores adversarial risk** — chunks that look like injected instructions, role overrides, or exfiltration attempts are surfaced as a risk signal, not silently trusted.
- **Emits an evidence record** — a structured per-query artifact (`query_id`, user, tenant, retrieved / allowed / blocked / redacted, policies triggered, tokens saved) that can be archived, replayed, and reviewed.

ContextGuard does **not** try to be a smarter retriever, a better model, or an LLM judge at runtime. It is a control plane around the context window.

## Who it is for

- **AI / platform engineers** building internal RAG or agentic systems and getting stuck on access control, multi-tenancy, and audit requirements.
- **Security teams** that need visibility into what their LLM-facing systems actually send out and receive back.
- **Compliance, DPO, and risk functions** that need *evidence* — not promises — to demonstrate control over AI data flows under EU AI Act, GDPR, and adjacent regimes.

## Why this, why now

Three forces are converging:

1. **RAG has moved from demo to production**, but production-grade access control, minimization, and auditability have not caught up.
2. **EU regulation is landing on AI systems** — the AI Act is staged into force, GDPR principles (minimization, integrity, accountability) apply to model inputs whether teams realize it or not, and sector regimes like DORA add explicit resilience-testing expectations.
3. **The market is full of "AI security" tools that scan prompts** and very few that control **context**. ContextGuard targets the layer most products skip.

> Disclaimer: ContextGuard is not a compliance certification and does not by itself make any system "AI Act compliant" or "GDPR compliant." It is an engineering control and evidence layer designed to support the technical controls and record-keeping that those regimes expect.

## Landscape — why this is not a duplicate

This is a competitive, well-funded space — and that is validation, not a warning. The category exists; what is missing is *this specific combination*. The market splits roughly into four buckets, and ContextGuard deliberately sits in the gap between them:

| Bucket | Examples | What they do | What they skip |
|---|---|---|---|
| **LLM / AI firewalls** | Lakera Guard, Protect AI (LLM Guard), Robust Intelligence (Cisco), NVIDIA NeMo Guardrails, Guardrails AI, Prompt Security | Prompt-injection, jailbreak, PII/toxicity, output filtering — **content** controls | They do not ask *"is this user allowed to see this document, in this classification?"* This is content filtering, not access control. |
| **Access control / authz for RAG** | Oso, Cerbos, Permit.io, Aserto, Pinecone metadata filtering, AWS Bedrock KB filtering, Glean, M365 Copilot | Filter documents by permission at retrieval time | Weak on the **proof**: they return a result, but rarely emit an audit-ready, versioned record of *why*. Enterprise players (Glean/Copilot) do this — but closed, SaaS, paywalled, not offline. |
| **LLM observability / eval** | Langfuse, Arize Phoenix, LangSmith, RAGAS, Helicone | Tracing, eval, cost | These are ContextGuard's **tools** (see ADR-003), not competitors. |
| **Data governance / DLP** | Microsoft Purview, BigID, Immuta, Cyera | Govern data at the storage layer | They operate on data-at-rest, not on the RAG query hot path. Complementary, not the same. |

**The white space ContextGuard targets** is the intersection no single self-hosted, open project assembles as a whole:

1. **Policy enforced at the point of retrieval** (`WHERE policy AND vector <-> $1`) — not a content post-filter.
2. **Evidence record as a versioned contract** (semver, replay-determinism) — a provable artifact, not a log line.
3. **Regulatory mapping (GDPR / AI Act) + offline-first + framework-agnostic core.**

The honest framing: the big players hold fragments behind a SaaS paywall, and open source has the separate building blocks that nobody has assembled into one coherent, audit-ready product. ContextGuard does not try to out-build Lakera on prompt injection — it owns a narrower corner: **"was this context allowed to be here — and prove it."**

## Core design principles

- **Defense in depth.** No single check is trusted to be perfect. Policy, classification, redaction, and risk scoring are layered.
- **Enforcement before generation.** Access decisions happen at retrieval time, on chunks, before the prompt is built — not after the model has already seen the data.
- **No LLM-as-judge at runtime.** Models are not used as the security boundary on the hot path. LLM-based evaluation is reserved for offline evals and red-teaming.
- **Evidence over claims.** Every decision the system makes is a record you can export, diff, and review.
- **Tenant isolation is a first-class concept**, not a filter bolted on at the end.

## Repository layout

This repository is a monorepo. It contains the product, the documentation, and the public learning trail behind it.

```
.
├── apps/
│   ├── api/              # Python backend — retrieval, policy engine, evidence emitter
│   └── web/              # Vue frontend — query console, policy editor, evidence viewer
├── packages/             # Shared schemas, policy DSL, evaluation harness
├── data/                 # Tenant fixtures, sample documents, red-team corpora
├── docs/
│   └── plan/       # The build plan that underpins every design decision
├── architecture notes          # Architecture decision records (ADRs)
└── README.md             # You are here
```

Implementation plans for `apps/api` and `apps/web`, the policy DSL, and the evidence schema are tracked separately and will land in `docs/` as they stabilize.

## Status

Early development. Built in the open as a portfolio and learning project, with the explicit goal of becoming a usable demonstrator and, eventually, a real product.

The accompanying [build plan](docs/plan/README.md) maps every concept used in ContextGuard — retrieval, context engineering, prompt security, evals, agentic patterns, EU AI regulation — to the stage of the product where it is applied. Reading the codebase and reading the build plan are meant to reinforce each other.

## License & legal

To be decided before the first external release. Nothing in this repository is legal advice.
