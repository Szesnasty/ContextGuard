"""Integration tests for the local compose stack (plan step 0.3).

These are opt-in: they require Docker + a running stack (`make up`). When the
stack is not up, they SKIP rather than fail, so `make test` stays green in the
zero-infra core workflow (ADR-010). Run explicitly after `make up`:

    make up && uv run pytest apps/api/tests/integration -m integration
"""

from __future__ import annotations

import socket
import subprocess
import urllib.request

import pytest

pytestmark = pytest.mark.integration

PG_PORT = 5432
REDIS_PORT = 6379
OLLAMA_PORT = 11434
LANGFUSE_PORT = 3001


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _stack_up() -> bool:
    return _port_open("localhost", PG_PORT) and _port_open("localhost", REDIS_PORT)


requires_stack = pytest.mark.skipif(
    not _stack_up(),
    reason="local compose stack not running (run `make up`)",
)


@requires_stack
def test_postgres_pgvector_roundtrip() -> None:
    """pgvector extension is installable and a <-> distance query works."""
    psycopg = pytest.importorskip("psycopg")
    dsn = "postgresql://contextguard:contextguard@localhost:5432/contextguard"
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute("CREATE TEMP TABLE _v (id int, emb vector(3));")
        cur.execute("INSERT INTO _v VALUES (1, '[1,0,0]'), (2, '[0,1,0]');")
        cur.execute("SELECT id FROM _v ORDER BY emb <-> '[1,0,0]' LIMIT 1;")
        row = cur.fetchone()
        assert row is not None and row[0] == 1


@requires_stack
def test_redis_roundtrip() -> None:
    redis = pytest.importorskip("redis")
    client = redis.Redis(host="localhost", port=REDIS_PORT, db=0)
    client.set("contextguard:ping", "pong")
    assert client.get("contextguard:ping") == b"pong"
    client.delete("contextguard:ping")


@requires_stack
def test_ollama_reachable() -> None:
    with urllib.request.urlopen(
        f"http://localhost:{OLLAMA_PORT}/api/tags", timeout=5
    ) as resp:
        assert resp.status == 200


@requires_stack
def test_langfuse_health() -> None:
    with urllib.request.urlopen(
        f"http://localhost:{LANGFUSE_PORT}/api/public/health", timeout=5
    ) as resp:
        assert resp.status == 200


@requires_stack
def test_all_services_healthy() -> None:
    """`docker compose ps` reports no unhealthy/exited service."""
    out = subprocess.run(
        ["docker", "compose", "ps", "--format", "{{.Name}} {{.State}} {{.Health}}"],
        capture_output=True,
        text=True,
        check=True,
    )
    for line in out.stdout.splitlines():
        if not line.strip() or "ollama-pull" in line:
            continue  # one-shot puller is expected to exit
        assert "exited" not in line.lower(), f"service down: {line}"
