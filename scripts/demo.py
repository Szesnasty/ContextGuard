"""Run the local ContextGuard demo end to end.

`make demo` should be the command a reviewer can trust: bring up the local
services, seed the planted corpus, start the API, start the Vue dashboard, and
print the URLs. It intentionally stays local/offline-first; cloud credentials
are not required.
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Sequence

DEFAULT_API_PORT = "8000"
DEFAULT_WEB_PORT = "5173"
_HOST = "127.0.0.1"


def _run(cmd: Sequence[str], *, env: dict[str, str] | None = None) -> None:
    print(f"demo: {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True, env=env)  # noqa: S603 - fixed local demo commands.


def _spawn(cmd: Sequence[str], *, env: dict[str, str] | None = None) -> subprocess.Popen[bytes]:
    print(f"demo: starting {' '.join(cmd)}", flush=True)
    return subprocess.Popen(cmd, env=env)  # noqa: S603 - fixed local demo commands.


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((_HOST, port))
        except OSError:
            return False
    return True


def _choose_port(requested: str, *, label: str) -> str:
    start = int(requested)
    for port in range(start, start + 50):
        if _port_is_free(port):
            if port != start:
                print(f"demo: {label} port {start} is busy; using {port}", flush=True)
            return str(port)
    raise RuntimeError(f"no free {label} port found in range {start}-{start + 49}")


def _wait_http(
    url: str,
    *,
    timeout: float = 60.0,
    children: Sequence[subprocess.Popen[bytes]] = (),
) -> bool:
    import urllib.error
    import urllib.request

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(child.poll() is not None for child in children):
            return False
        try:
            with urllib.request.urlopen(url, timeout=2.0) as response:  # noqa: S310
                if 200 <= response.status < 500:
                    return True
        except (OSError, urllib.error.URLError):
            time.sleep(1.0)
    return False


def main() -> int:
    env = os.environ.copy()
    env.setdefault("POLICY_PATH", "data/policies/example.yaml")
    env.setdefault("EVIDENCE_SINK", "postgres")
    env.setdefault("OLLAMA_CHAT_MODEL", "llama3.2:3b")
    env.setdefault("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    env.setdefault("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    try:
        api_port = _choose_port(env.get("API_PORT", DEFAULT_API_PORT), label="API")
        web_port = _choose_port(env.get("WEB_PORT", DEFAULT_WEB_PORT), label="dashboard")
    except ValueError as exc:
        print(f"demo: invalid port: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"demo: {exc}", file=sys.stderr)
        return 2
    api_url = f"http://{_HOST}:{api_port}"
    web_url = f"http://{_HOST}:{web_port}"
    env["API_PORT"] = api_port
    env["WEB_PORT"] = web_port
    env["VITE_API_PROXY"] = api_url

    try:
        _run(["docker", "compose", "up", "-d", "--wait"], env=env)
        _run([sys.executable, "scripts/seed.py"], env=env)
        _run(["pnpm", "--filter", "@contextguard/web", "run", "copy:reports"], env=env)
    except FileNotFoundError as exc:
        print(f"demo: missing executable: {exc.filename}", file=sys.stderr)
        return 127
    except subprocess.CalledProcessError as exc:
        print(f"demo: setup failed with exit code {exc.returncode}", file=sys.stderr)
        return exc.returncode

    api = _spawn(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "contextguard.api.app:create_app",
            "--factory",
            "--reload",
            "--port",
            api_port,
        ],
        env=env,
    )
    web = _spawn(
        [
            "pnpm",
            "--filter",
            "@contextguard/web",
            "exec",
            "vite",
            "--host",
            _HOST,
            "--port",
            web_port,
            "--strictPort",
        ],
        env=env,
    )
    children = [api, web]

    def stop(_signum: int | None = None, _frame: object | None = None) -> None:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    api_ready = _wait_http(f"{api_url}/health", children=[api])
    web_ready = _wait_http(web_url, children=[web])
    print("", flush=True)
    if not api_ready or not web_ready:
        print("ContextGuard demo failed to start.", flush=True)
        for name, child in (("API", api), ("Dashboard", web)):
            if child.poll() is not None:
                print(f"  {name} exited with code {child.returncode}", flush=True)
        stop()
        return 1

    print("ContextGuard demo is ready.", flush=True)
    print(f"  API:       {api_url}", flush=True)
    print(f"  Dashboard: {web_url}", flush=True)
    print("  Demo identity: generate a token in the dashboard for sales@acme", flush=True)
    print("  Try: Are we acquiring any company soon, and for how much?", flush=True)
    print("", flush=True)
    print(
        "Press Ctrl+C to stop API and dashboard. Compose services keep running; use `make down`.",
        flush=True,
    )

    try:
        while True:
            for name, child in (("API", api), ("Dashboard", web)):
                code = child.poll()
                if code is not None:
                    print(f"demo: {name} exited with code {code}", file=sys.stderr)
                    return code or 1
            time.sleep(1.0)
    finally:
        stop()


if __name__ == "__main__":
    raise SystemExit(main())
