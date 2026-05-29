"""Integration tier: hit a real uvicorn server over HTTP.

Marked `integration` so the core run skips it. Spawns its own uvicorn on an
ephemeral port; no compose services needed for this particular smoke test, but
it exercises the real ASGI server rather than the in-process TestClient.
"""

from __future__ import annotations

import socket
import time
import urllib.request
from collections.abc import Iterator
from contextlib import closing
from multiprocessing import Process

import pytest
import uvicorn

pytestmark = pytest.mark.integration


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _serve(port: int) -> None:
    uvicorn.run(
        "contextguard.api.app:create_app",
        factory=True,
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )


@pytest.fixture
def live_server() -> Iterator[str]:
    port = _free_port()
    proc = Process(target=_serve, args=(port,), daemon=True)
    proc.start()
    base = f"http://127.0.0.1:{port}"
    try:
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                urllib.request.urlopen(f"{base}/health", timeout=1)
                break
            except OSError:
                time.sleep(0.2)
        else:
            pytest.fail("uvicorn did not become ready in time")
        yield base
    finally:
        proc.terminate()
        proc.join(timeout=5)


def test_health_over_http(live_server: str) -> None:
    with urllib.request.urlopen(f"{live_server}/health", timeout=5) as resp:
        assert resp.status == 200
