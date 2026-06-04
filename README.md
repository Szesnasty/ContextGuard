# ContextGuard

[![CI](https://github.com/Szesnasty/ContextGuard/actions/workflows/ci.yml/badge.svg)](https://github.com/Szesnasty/ContextGuard/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/Szesnasty/ContextGuard?sort=semver)](https://github.com/Szesnasty/ContextGuard/releases/latest)
[![License](https://img.shields.io/github/license/Szesnasty/ContextGuard)](LICENSE)

**A context firewall for RAG systems.**

ContextGuard sits between retrieval and generation. It decides which chunks are
allowed to reach the model, which must be redacted, which must be blocked, and
why. Every decision becomes evidence you can inspect, replay, and test.

It is library-first: the core guard can run without Docker, a database, a model,
or network access.

Most RAG systems ask:

> Did we retrieve relevant context?

ContextGuard asks:

> Was this user allowed to retrieve this context, and can we prove it?

Use it when:

- your RAG system uses private, internal, or multi-tenant data,
- you need per-chunk `allow`, `redact`, and `block` decisions,
- you need evidence for why context reached the model.

---

## Why It Exists

Production RAG is no longer only a relevance problem. Internal assistants now
retrieve contracts, tickets, HR files, roadmap notes, customer data, source code,
and tenant-specific knowledge. The retrieval layer is often optimized for
semantic match, while access control, minimization, and auditability live
somewhere else.

That creates a sharp failure mode: the vector store can retrieve the right chunk
for the question, but the wrong chunk for the user.

ContextGuard is the control plane for that boundary:

- **Tenant isolation** - an `acme` user should never receive `contoso` context.
- **Role and classification policy** - sales can use public/internal docs, but
  not confidential M&A notes.
- **Data minimization** - PII and secrets can be masked before prompt assembly.
- **Indirect injection defense** - poisoned documents are treated as risk
  signals, not trusted instructions.
- **Evidence over promises** - each query records what was retrieved, allowed,
  redacted, blocked, and which policy fired.

ContextGuard is not trying to be a better retriever or a smarter model. It is a
small, explicit enforcement layer around the context window.

## Usage Modes

ContextGuard is designed around two usage modes:

1. **Core library** - a zero-infra Python guard that takes `UserContext`, a
   query, and candidate chunks, then returns allowed, redacted, and blocked
   chunks plus an evidence record. This is the primary product surface. Public
   package publication is planned after the package naming and distribution
   pass.
2. **Local demo stack** - a reference RAG system with FastAPI, pgvector, Ollama,
   and a Vue dashboard, used to demonstrate policy-aware retrieval, evidence,
   and leak prevention end to end.

## Latest Release

The latest stable source release is
[`v1.0.0`](https://github.com/Szesnasty/ContextGuard/releases/tag/v1.0.0).
The default branch tracks current development; versioned tags are the stable
snapshots.

Until the Python packages are published to a public package index, install the
1.0.0 wheels from the GitHub release:

```bash
uv venv
uv pip install \
  https://github.com/Szesnasty/ContextGuard/releases/download/v1.0.0/contextguard_contracts-1.0.0-py3-none-any.whl \
  https://github.com/Szesnasty/ContextGuard/releases/download/v1.0.0/contextguard_policy_dsl-1.0.0-py3-none-any.whl \
  https://github.com/Szesnasty/ContextGuard/releases/download/v1.0.0/contextguard-1.0.0-py3-none-any.whl
```

For the full local demo, clone the repository and use `make demo`.

## Product Tour

The dashboard shows the security boundary in plain sight: retrieval can find a
chunk, but policy decides whether that chunk may reach the model for this
identity.

### RAG Console

![RAG Console showing a support identity, a cross-tenant prompt, and allowed/redacted/blocked source counts.](docs/img/rag-console-cross-tenant.png)

Ask a normal RAG question and see the context firewall summarize what happened:
how many sources were allowed, redacted, or blocked before the answer was
generated.

### Evidence Decision Flow

![Evidence Viewer showing retrieved chunks passing through the policy gate into allowed, redacted, blocked, and prompt outcomes.](docs/img/evidence-decision-flow.png)

Replay a query as an evidence record. The flow makes the invariant visible:
retrieved chunks pass through a policy gate before the prompt is assembled.

### Context Delta And Enforced Decisions

![Evidence Viewer showing context withheld from the model and the policy decisions behind each blocked or redacted chunk.](docs/img/context-delta-enforced-decisions.png)

Inspect the exact context delta: withheld chunks are shown separately, redacted
PII is masked, and every enforced decision points back to a policy rule.

## Core Library Quickstart

The core is designed to run as a Python library. It works inside this repo
without Docker, a database, a model, or network access. A public package release
is planned after the package naming and distribution pass.

```python
from contextguard import ContextGuard
from contextguard.core.types import Chunk, Classification, UserContext

guard = ContextGuard.from_policy("data/policies/example.yaml")

user = UserContext(
    sub="sales@acme",
    tenant="acme",
    role="sales",
    purpose="support",
)

chunks = [
    Chunk(
        id="public-faq",
        doc_id="faq",
        tenant="acme",
        classification=Classification.PUBLIC,
        text="Refund requests are handled by support.",
    ),
    Chunk(
        id="secret-mna",
        doc_id="mna-falcon",
        tenant="acme",
        classification=Classification.CONFIDENTIAL,
        text="Project Falcon acquisition target is Initech for 1.2B.",
    ),
]

result = guard.guard(user, "Are we acquiring anyone?", chunks)

print([chunk.id for chunk in result.allowed_chunks])
print(guard.last_evidence())
```

## Demo Quickstart

Prerequisites:

- Docker Desktop
- Python 3.12
- Node 20+
- `uv`
- `pnpm`

Optional local configuration:

```bash
cp .env.example .env
```

You can skip this step if the default ports are free. `make demo` reads `.env`
automatically when present.

Run the local demo:

```bash
make demo
```

The command starts the local stack, prepares the database, seeds the planted
tenant corpus, starts the FastAPI backend, and starts the Vue dashboard.

Open the dashboard:

```text
http://localhost:5173
```

In the dashboard:

1. Generate a dev token for `sales@acme`.
2. Ask:

```text
Are we acquiring any company soon, and for how much?
```

3. Open the sources/evidence drawer.
4. Look for the confidential acquisition chunk: it may be retrieved, but it is
   withheld from the model and attributed to the policy rule that blocked it.

Run the fast demo smoke test against a running API:

```bash
make e2e
```

If local ports collide with another stack, override them:

```bash
POSTGRES_PORT=55432 \
DATABASE_URL=postgresql://contextguard:contextguard@localhost:55432/contextguard \
REDIS_PORT=6380 \
REDIS_URL=redis://localhost:6380/0 \
LANGFUSE_PORT=3002 \
OLLAMA_PORT=11435 \
OLLAMA_BASE_URL=http://127.0.0.1:11435 \
API_PORT=8008 \
WEB_PORT=5174 \
make demo
```

Then run:

```bash
API_BASE=http://127.0.0.1:8008 make e2e
```

## What The Demo Shows

The planted demo corpus contains ordinary product/support documents plus
intentional leak surfaces:

- a confidential `acme` M&A memo,
- a cross-tenant `contoso` chunk,
- PII-bearing support text,
- a secret-bearing runbook chunk,
- an indirect prompt-injection document.

For a `sales@acme` identity, ContextGuard demonstrates:

- retrieval provenance,
- per-chunk `allowed`, `redacted`, and `blocked` decisions,
- token reduction before vs. after the firewall,
- policy reasons such as `tenant-isolation` and `sales-no-confidential`,
- a query-level evidence record.

The important security invariant:

**blocked chunk text does not reach the model and is not returned by `/v1/query`
as raw retrieved text.**

## How It Works

```mermaid
flowchart LR
    U["User query + signed identity"] --> A["FastAPI adapter"]
    A --> R["Hybrid retriever<br/>pgvector kNN + BM25"]
    R --> C["Candidate chunks"]
    C --> E1
    E3 --> P["Allowed + redacted chunks"]
    P --> PB["Prompt builder<br/>cited context only"]
    PB --> L["LLM gateway<br/>Ollama by default"]
    L --> O["Grounded answer"]
    E3 --> E["Evidence record"]

    subgraph Guard["Context firewall"]
        E1["Enrich<br/>PII, secrets, injection signals"]
        E2["Policy<br/>tenant, role, classification"]
        E3["Redact / block / allow"]
        E1 --> E2 --> E3
    end
```

### Decision Pipeline

```mermaid
flowchart TD
    Q["Query"] --> K["Top-k retrieval"]
    K --> C1["Chunk: public/internal"]
    K --> C2["Chunk: confidential"]
    K --> C3["Chunk: cross-tenant"]
    K --> C4["Chunk: PII or secret"]
    K --> C5["Chunk: injection risk"]

    C1 --> A["Allowed"]
    C2 --> B["Blocked<br/>sales-no-confidential"]
    C3 --> T["Blocked<br/>tenant-isolation"]
    C4 --> D["Redacted<br/>redact-pii / redact-secrets"]
    C5 --> I["Blocked<br/>block-injection"]

    A --> P["Prompt context"]
    D --> P
    B --> X["Withheld from model"]
    T --> X
    I --> X
    P --> M["Model answer"]

    A --> EV["Evidence"]
    B --> EV
    T --> EV
    D --> EV
    I --> EV
```

### Repository Architecture

```mermaid
flowchart TB
    Web["apps/web<br/>Vue dashboard"] --> API["contextguard.api<br/>FastAPI adapter"]
    API --> Query["/v1/query<br/>retrieve -> guard -> prompt -> LLM"]
    API --> Scan["/v1/guard<br/>scan-only verdict"]
    Query --> Retrieval["retrieval<br/>pgvector kNN + BM25"]
    Query --> Core["contextguard.core<br/>zero-infra guard"]
    Query --> Prompt["prompt builder<br/>allowed chunks only"]
    Prompt --> LLM["llm gateway<br/>Ollama by default"]
    Scan --> Core
    API --> Metrics["/metrics<br/>Prometheus format"]

    Core --> Contracts["packages/contracts<br/>Pydantic models + JSON Schema"]
    Core --> Policy["packages/policy-dsl<br/>YAML policy evaluator"]
    Core --> Evidence["EvidenceSink protocol<br/>in-memory / JSONL default"]
    API --> PgEvidence["optional Postgres JSONB evidence<br/>EVIDENCE_SINK=postgres"]
    PgEvidence --> Evidence

    Eval["packages/eval-harness<br/>benchmarks + red-team corpus"] --> Core
    Data["data/<br/>tenants, users, policies, attacks"] --> Retrieval
    Data --> Eval

    Compose["compose.yaml<br/>Postgres, Redis, Ollama, Langfuse"] --> API
```

## Policy Examples

Policies are declarative YAML. Rules are evaluated by priority. The first match
wins; if no rule matches, the `default_effect` applies.

The demo policy is permissive by default so the planted examples are easy to
compare:

```yaml
version: 1
default_effect: allow

roles:
  manager:
    inherits: [sales]

rules:
  - id: tenant-isolation
    effect: deny
    priority: 100
    when:
      - { field: chunk.tenant, op: neq, ref: user.tenant }

  - id: sales-no-confidential
    effect: deny
    priority: 50
    when:
      - { field: user.roles, op: contains, value: sales }
      - { field: chunk.classification, op: gte, value: confidential }

  - id: redact-pii
    effect: redact
    priority: 30
    when:
      - { field: chunk.pii_count, op: gte, value: 1 }
```

For a production-style posture, start deny-by-default and add explicit allow
rules after stricter deny/redact rules:

```yaml
version: 1
default_effect: deny

rules:
  - id: tenant-isolation
    effect: deny
    priority: 100
    when:
      - { field: chunk.tenant, op: neq, ref: user.tenant }

  - id: allow-safe-context
    effect: allow
    priority: 10
    when:
      - { field: chunk.tenant, op: eq, ref: user.tenant }
```

See [`data/policies/example.yaml`](data/policies/example.yaml) and
[`data/policies/strict.yaml`](data/policies/strict.yaml).

## Proof Points

The current benchmark and red-team reports are deterministic. They do not use an
LLM judge.

| Artifact | Result |
|---|---|
| `make test` | 336 Python tests + 18 frontend tests passed |
| `make lint` | Python and frontend lint clean |
| `make types` | mypy + Vue typecheck passed |
| `make benchmark` | on the planted demo corpus: policy off 100% leak rate, policy on 0% leak rate |
| `make red-team` | on the committed adversarial corpus: 6/6 cases passed, 0% leak rate, 0 replay mismatches |
| `make e2e` | fast local demo smoke test |

See:

- [BENCHMARK.md](BENCHMARK.md)
- [RED-TEAM.md](RED-TEAM.md)

## What Makes It Different

ContextGuard is not a generic LLM firewall. It focuses on the context boundary:

| Category | Typical focus | ContextGuard focus |
|---|---|---|
| LLM firewalls | prompt/output content filtering | what context is allowed before generation |
| RAG retrieval tools | relevance and ranking | policy-aware retrieval and minimization |
| Observability tools | traces, cost, evals | evidence as an auditable product contract |
| Data governance tools | data at rest | RAG query hot path |

The product thesis is narrow on purpose:

**Was this context allowed to be here, and can we prove it?**

## What ContextGuard Is Not

ContextGuard is not:

- a replacement for your retriever,
- a replacement for identity or ACL mapping,
- a replacement for secure source-system permissions,
- a generic LLM firewall,
- a compliance certification,
- a guarantee that no data can ever leak.

## Project Layout

```text
.
├── apps/
│   └── web/                     # Vue dashboard + frontend README
├── packages/
│   ├── contextguard/            # Python core, API adapter, retrieval, evidence
│   ├── contracts/               # Pydantic contracts + JSON Schemas + OpenAPI
│   ├── policy-dsl/              # YAML policy schema and evaluator
│   └── eval-harness/            # benchmarks and red-team runner
├── data/
│   ├── tenants/                 # planted demo corpus
│   ├── policies/                # demo + strict policies
│   └── red-team-corpora/        # golden adversarial cases
├── docs/
│   └── img/                     # README screenshots
├── compose.yaml                 # local stack
├── CHANGELOG.md                 # release notes
├── CONTRIBUTING.md              # contribution guide
├── ROADMAP.md                   # next milestones
├── SECURITY.md                  # vulnerability reporting scope
├── Makefile                     # canonical dev/demo commands
└── README.md
```

## Status

ContextGuard 1.0.0 is the first official MVP release, built in the open. It is
ready to demonstrate the product thesis locally:

- policy-aware context filtering,
- redaction and blocking,
- evidence records,
- red-team and benchmark artifacts,
- a dashboard for query, sources, policy, and evidence review.

It is not a compliance certification, legal opinion, or production deployment
template. Real production use would still need hardened identity, connector-level
ACL mapping, retention policy, deployment hardening, and a fuller security
review.

## License

ContextGuard is licensed under the Apache License 2.0. See [LICENSE](LICENSE).

## Legal

ContextGuard is not legal advice and does not by itself make a system compliant
with GDPR, the EU AI Act, DORA, or any other regime. It is an engineering control
and evidence layer intended to support stronger AI data-flow governance.
