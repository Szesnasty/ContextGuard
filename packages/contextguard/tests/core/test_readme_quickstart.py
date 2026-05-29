"""The README quickstart is a real, offline, passing test (Milestone A5, §6a item 6).

The ~5-line drop-in snippet in `packages/contextguard/README.md` is the first
thing an adopter runs. This test extracts that exact ```python``` block from the
README and executes it with networking disabled, so the published quickstart can
never silently rot: if the snippet stops working offline, this test goes red.
"""

from __future__ import annotations

import re
import socket
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
README = PACKAGE_ROOT / "README.md"
POLICY_PATH = PACKAGE_ROOT.parents[1] / "data" / "policies" / "example.yaml"


def _quickstart_code() -> str:
    text = README.read_text(encoding="utf-8")
    block = re.search(r"## Quickstart\s+```python\n(.*?)```", text, re.DOTALL)
    assert block is not None, "README must contain a ```python``` quickstart block"
    code = block.group(1)
    # The published snippet references a local "policy.yaml"; point it at the
    # shipped example policy so the test runs without a fixture file.
    return code.replace('"policy.yaml"', f'r"{POLICY_PATH}"')


def test_readme_quickstart_runs_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise OSError("network disabled")

    monkeypatch.setattr(socket, "socket", _boom)
    namespace: dict[str, object] = {}
    exec(_quickstart_code(), namespace)

    result = namespace["result"]
    guard = namespace["guard"]
    assert [c.id for c in result.allowed_chunks] == ["c1"]  # type: ignore[attr-defined]
    evidence = guard.last_evidence()  # type: ignore[attr-defined]
    assert isinstance(evidence, dict)
    assert evidence["query"] == "what is our refund policy?"
