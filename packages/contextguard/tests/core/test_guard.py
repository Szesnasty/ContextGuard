"""Guard pass-through + zero-infra tests (step 1.4, ADR-010)."""

from __future__ import annotations

import socket
from pathlib import Path

import pytest
from contextguard.core import ContextGuard
from contextguard.core.types import Chunk, Classification, Outcome, UserContext


def _user() -> UserContext:
    return UserContext(sub="u1", tenant="acme", role="sales", purpose="support")


def _chunks(n: int) -> list[Chunk]:
    return [
        Chunk(
            id=f"c{i}",
            doc_id="d1",
            tenant="acme",
            text=f"chunk number {i}",
            classification=Classification.PUBLIC,
        )
        for i in range(n)
    ]


def test_guard_allows_all() -> None:
    chunks = _chunks(3)
    result = ContextGuard().guard(_user(), "hi", chunks)
    assert {c.id for c in result.allowed_chunks} == {c.id for c in chunks}


def test_guard_one_decision_per_chunk_all_allowed() -> None:
    chunks = _chunks(4)
    result = ContextGuard().guard(_user(), "hi", chunks)
    assert len(result.decisions) == len(chunks)
    assert all(d.outcome == Outcome.ALLOWED for d in result.decisions)
    assert {d.chunk_id for d in result.decisions} == {c.id for c in chunks}


def test_guard_tokens_equal_in_passthrough() -> None:
    result = ContextGuard().guard(_user(), "hi", _chunks(3))
    assert result.tokens_before == result.tokens_after
    assert result.tokens_before > 0


def test_guard_empty_input() -> None:
    result = ContextGuard().guard(_user(), "hi", [])
    assert result.allowed_chunks == []
    assert result.decisions == []
    assert result.tokens_before == 0
    assert result.tokens_after == 0


def test_guard_is_deterministic() -> None:
    chunks = _chunks(3)
    g = ContextGuard()
    assert g.guard(_user(), "hi", chunks) == g.guard(_user(), "hi", chunks)


def test_guard_no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise OSError("network disabled")

    monkeypatch.setattr(socket, "socket", _boom)
    result = ContextGuard().guard(_user(), "hi", _chunks(2))
    assert len(result.allowed_chunks) == 2


def test_from_policy_zero_infra(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    policy_file = tmp_path / "policy.yaml"
    policy_file.write_text("version: 1\nrules: []\n", encoding="utf-8")

    def _boom(*args: object, **kwargs: object) -> None:
        raise OSError("network disabled")

    monkeypatch.setattr(socket, "socket", _boom)
    guard = ContextGuard.from_policy(policy_file)
    assert guard.policy is not None
    assert guard.policy.version == 1
    result = guard.guard(_user(), "hi", _chunks(1))
    assert len(result.allowed_chunks) == 1


def test_from_policy_rejects_non_mapping(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        ContextGuard.from_policy(bad)


def test_evidence_dict_and_no_disk_without_path() -> None:
    guard = ContextGuard()
    assert guard.last_evidence() is None
    guard.guard(_user(), "hi", _chunks(2))
    ev = guard.last_evidence()
    assert isinstance(ev, dict)
    assert ev["schema_version"] == "0.1"
    assert ev["metrics"]["chunks_allowed"] == 2


def test_evidence_jsonl_appended_when_path_set(tmp_path: Path) -> None:
    path = tmp_path / "ev.jsonl"
    guard = ContextGuard(evidence_path=path)
    guard.guard(_user(), "hi", _chunks(1))
    guard.guard(_user(), "bye", _chunks(1))
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


def test_quickstart_snippet_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise OSError("network disabled")

    monkeypatch.setattr(socket, "socket", _boom)
    guard = ContextGuard()
    user = UserContext(sub="u1", tenant="acme", role="sales", purpose="support")
    chunks = [
        Chunk(
            id="c1",
            doc_id="d1",
            tenant="acme",
            text="hello world",
            classification=Classification.PUBLIC,
        )
    ]
    result = guard.guard(user, "hi", chunks)
    assert result.allowed_chunks
    assert guard.last_evidence() is not None


def test_no_heavy_imports() -> None:
    """A clean ``import contextguard.core`` pulls no heavy infra (ADR-010).

    Runs in a subprocess so the shared pytest process (which loads FastAPI via
    conftest) does not pollute the check.
    """
    import subprocess
    import sys

    code = (
        "import sys; import contextguard.core; "
        "heavy={'psycopg','sqlalchemy','redis','litellm','presidio_analyzer',"
        "'sentence_transformers','tiktoken','fastapi','uvicorn'}; "
        "bad=sorted(heavy & set(sys.modules)); "
        "print(','.join(bad)); sys.exit(1 if bad else 0)"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"heavy imports pulled by core: {proc.stdout.strip()}"


def test_public_top_level_import() -> None:
    """`from contextguard import ContextGuard` works and stays zero-infra (ADR-013).

    This is the exact entry point the README quickstart and Public v0.1 promise.
    Runs in a subprocess so the bare top-level import is measured in isolation.
    """
    import subprocess
    import sys

    code = (
        "import sys; from contextguard import ContextGuard, __version__; "
        "assert ContextGuard.__name__ == 'ContextGuard'; "
        "heavy={'fastapi','uvicorn','structlog','psycopg','sqlalchemy','redis'}; "
        "bad=sorted(heavy & set(sys.modules)); "
        "print(','.join(bad)); sys.exit(1 if bad else 0)"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"top-level import pulled heavy deps: {proc.stdout.strip()}"
