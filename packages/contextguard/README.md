# contextguard

Policy-aware context firewall for production RAG — a zero-infra Python library.

`ContextGuard` decides, per chunk, what may reach your model: **allow / block /
redact**, driven by a declarative YAML policy. It runs in-memory with no
database, no network, and no model calls (ADR-010). Heavier capabilities
(HTTP API, Postgres, Presidio, …) are opt-in extras.

## Local Install

ContextGuard 1.0.0 is available as a GitHub source release. Public package
publication is planned after the package naming and distribution pass. Inside
this workspace, use the root development environment:

```bash
uv sync --frozen --all-packages
uv run python -c "from contextguard import ContextGuard; print(ContextGuard)"
```

## Quickstart

```python
from contextguard import ContextGuard
from contextguard.core.types import Chunk, Classification, UserContext

guard = ContextGuard.from_policy("policy.yaml")  # offline: no DB, no network

user = UserContext(sub="u1", tenant="acme", role="sales", purpose="support")
chunks = [
    Chunk(id="c1", doc_id="d1", tenant="acme", text="public info",
          classification=Classification.PUBLIC),
]

result = guard.guard(user, "what is our refund policy?", chunks)
print([c.id for c in result.allowed_chunks])  # what reaches the model
print(guard.last_evidence())                  # structured audit record (dict)
```

**ContextGuard does not guess permissions.** It enforces your policy against the
`UserContext` you pass in — map your own auth onto it.

## License

Apache License 2.0. See the repository-root `LICENSE` file.
