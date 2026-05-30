"""`make token SUB=sales@acme` - mint a demo identity token (B3.2, ADR-015).

Reads a demo identity from ``data/users.yaml`` and prints a signed JWT for it,
so the secured ``/v1/query`` path can be exercised by hand:

    TOKEN=$(make -s token SUB=sales@acme)
    curl -H "Authorization: Bearer $TOKEN" -d '{"query":"...","k":5}' .../v1/query

Demo/dev only (ADR-015): one symmetric secret (``JWT_SECRET`` or the dev
fallback). Real tokens come from an IdP.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from contextguard.auth import issue_token
from contextguard_contracts import UserContext

_USERS_PATH = Path(__file__).resolve().parents[1] / "data" / "users.yaml"


def _load_users() -> dict[str, UserContext]:
    raw = yaml.safe_load(_USERS_PATH.read_text(encoding="utf-8")) or {}
    return {u["sub"]: UserContext(**u) for u in raw.get("users", [])}


def main() -> int:
    parser = argparse.ArgumentParser(description="Mint a demo identity token.")
    parser.add_argument("sub", help="demo identity 'sub' from data/users.yaml (e.g. sales@acme)")
    args = parser.parse_args()

    users = _load_users()
    user = users.get(args.sub)
    if user is None:
        known = ", ".join(sorted(users)) or "(none)"
        print(f"unknown identity {args.sub!r}; known: {known}", file=sys.stderr)
        return 1

    print(issue_token(user))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
