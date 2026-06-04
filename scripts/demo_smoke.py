"""Smoke-test the local demo API.

This is intentionally faster than a live model e2e. It proves the demo server is
up, dev token minting works, the scan-only guard blocks a planted confidential
chunk for `sales@acme`, and product metrics are exposed.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000").rstrip("/")


def _request(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    token: str | None = None,
) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(  # noqa: S310 - local demo API only.
        f"{API_BASE}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=15.0) as response:  # noqa: S310
            raw = response.read().decode("utf-8")
            if response.headers.get("content-type", "").startswith("application/json"):
                return response.status, json.loads(raw)
            return response.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload: Any = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw
        return exc.code, payload


def _chunk(
    cid: str,
    *,
    doc_id: str,
    tenant: str,
    classification: str,
    text: str,
) -> dict[str, Any]:
    return {
        "id": cid,
        "doc_id": doc_id,
        "tenant": tenant,
        "classification": classification,
        "text": text,
        "metadata": {},
        "pii_spans": [],
        "secret_spans": [],
        "risk_signals": [],
    }


def main() -> int:
    status, health = _request("GET", "/health")
    if status != 200 or health.get("status") != "ok":
        print(f"e2e: /health failed: {status} {health}", file=sys.stderr)
        return 1

    status, minted = _request("POST", "/v1/dev/token", body={"sub": "sales@acme"})
    if status != 200:
        print(f"e2e: token mint failed: {status} {minted}", file=sys.stderr)
        return 1
    token = minted["token"]

    guard_body = {
        "query": "Are we acquiring any company soon?",
        "candidate_chunks": [
            _chunk(
                "benign",
                doc_id="acme-product-faq",
                tenant="acme",
                classification="internal",
                text="Acme refund requests are handled by support.",
            ),
            _chunk(
                "blocked-confidential",
                doc_id="acme-mna-falcon",
                tenant="acme",
                classification="confidential",
                text="Project Falcon acquisition target is Initech for 1.2B.",
            ),
            _chunk(
                "blocked-tenant",
                doc_id="contoso-pricing",
                tenant="contoso",
                classification="internal",
                text="Contoso internal pricing should not be visible to Acme.",
            ),
        ],
    }
    status, guarded = _request("POST", "/v1/guard", body=guard_body, token=token)
    if status != 200:
        print(f"e2e: /v1/guard failed: {status} {guarded}", file=sys.stderr)
        return 1

    decisions = {d["chunk_id"]: d for d in guarded["decisions"]}
    if decisions["benign"]["outcome"] != "allowed":
        print(f"e2e: benign chunk was not allowed: {decisions['benign']}", file=sys.stderr)
        return 1
    if decisions["blocked-confidential"]["outcome"] != "blocked":
        print(
            f"e2e: confidential chunk was not blocked: {decisions['blocked-confidential']}",
            file=sys.stderr,
        )
        return 1
    if decisions["blocked-tenant"]["outcome"] != "blocked":
        print(
            f"e2e: cross-tenant chunk was not blocked: {decisions['blocked-tenant']}",
            file=sys.stderr,
        )
        return 1

    status, metrics = _request("GET", "/metrics")
    if status != 200 or "cg_chunks_retrieved_total" not in metrics:
        print("e2e: product metrics were not exposed", file=sys.stderr)
        return 1

    print("e2e: demo smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
