#!/usr/bin/env python3
"""Repo-shape assertions for the ContextGuard monorepo layout (plan step 0.1).

Run: python3 scripts/check_layout.py
Exit code 0 = layout OK, 1 = violation. Intended to move into CI/pre-commit later.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Required top-level directories from ADR-003 §Decision.
REQUIRED_DIRS = [
    "apps/api",
    "apps/web",
    "packages/contracts",
    "packages/policy-dsl",
    "packages/eval-harness",
    "data/tenants/acme/docs",
    "data/tenants/contoso/docs",
    "data/policies",
    "data/red-team-corpora",
    "infra/docker",
    "infra/github-actions",
    "infra/seed",
]

# A markdown link pointing at the old labs path = stale reference. Prose/code
# mentions in the migration docs are allowed; broken *links* are not.
STALE_LINK = re.compile(r"\]\([^)]*labs/context-guard")


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}")


def check_required_dirs() -> list[str]:
    errors: list[str] = []
    for rel in REQUIRED_DIRS:
        if not (ROOT / rel).is_dir():
            errors.append(f"missing required directory: {rel}")
    return errors


def check_labs_absent() -> list[str]:
    if (ROOT / "labs").exists():
        return ["labs/ must not exist after migration (plan step 0.1)"]
    return []


def _tracked_markdown_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [ROOT / line for line in out.stdout.splitlines() if line]


def check_no_stale_links() -> list[str]:
    errors: list[str] = []
    for path in _tracked_markdown_files():
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if STALE_LINK.search(line):
                rel = path.relative_to(ROOT)
                errors.append(f"stale labs/context-guard link in {rel}:{n}")
    return errors


def main() -> int:
    errors: list[str] = []
    errors += check_required_dirs()
    errors += check_labs_absent()
    errors += check_no_stale_links()

    if errors:
        for e in errors:
            _fail(e)
        return 1

    print("OK: monorepo layout matches ADR-003; labs/ removed; no stale links.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
