"""Dump the API's OpenAPI document to a committed JSON snapshot.

Run via ``make openapi``. The output is deterministic (sorted keys,
newline-terminated) so the snapshot is byte-stable across runs and reviewable in
diffs. It feeds the typed frontend client: ``openapi-typescript`` turns this
document into ``apps/web/src/api/schema.d.ts`` (Milestone B6, ADR-004 keeps the
contracts the single source of truth for both Python and TypeScript).

Zero-infra: the document is produced from ``create_app().openapi()`` in-process;
no server, database, or model is started.
"""

from __future__ import annotations

import json
from pathlib import Path

from contextguard.api.app import create_app

OUTPUT = Path(__file__).resolve().parent.parent / "packages" / "contracts" / "ts" / "openapi.json"


def render() -> str:
    """Render the OpenAPI document as deterministic, newline-terminated JSON."""
    schema = create_app().openapi()
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def write(target: Path = OUTPUT) -> Path:
    """Write the OpenAPI snapshot; return the path written."""
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(), encoding="utf-8")
    return target


def main() -> None:
    print(f"wrote {write()}")


if __name__ == "__main__":
    main()
