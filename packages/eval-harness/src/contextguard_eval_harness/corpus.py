"""Seed-corpus loader — parse the planted-leak tenant documents (Milestone B1.1).

The corpus lives under ``data/tenants/<tenant>/docs/*.md``; each file carries
YAML frontmatter (``doc_id``, ``tenant``, ``classification``, ``title`` + optional
leak flags) followed by the Markdown body. This loader is **zero-infra** — it
reads files and parses ``pyyaml``, nothing heavier — so the corpus-shape tests
and the (later, Tier A) chunker can both consume one canonical representation.

The chunker in step B1.2 inherits ``doc_id`` / ``tenant`` / ``classification``
from each :class:`Document` returned here, which is how a chunk knows the
sensitivity it must be policed against (ADR-005: ContextGuard enforces metadata,
it does not invent it).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from contextguard_contracts import Classification

# Repo root = three parents up from this file's package (…/packages/eval-harness/
# src/contextguard_eval_harness/corpus.py → repo root).
_REPO_ROOT = Path(__file__).resolve().parents[4]
TENANTS_DIR = _REPO_ROOT / "data" / "tenants"

_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.DOTALL)


@dataclass(frozen=True)
class Document:
    """One seed document: inherited metadata + body, plus its leak flags."""

    doc_id: str
    tenant: str
    classification: Classification
    title: str
    text: str
    path: Path
    flags: dict[str, bool] = field(default_factory=dict)

    @property
    def is_leak_target(self) -> bool:
        return bool(self.flags.get("leak_target"))

    @property
    def is_cross_tenant_trap(self) -> bool:
        return bool(self.flags.get("cross_tenant_trap"))


def parse_document(path: Path) -> Document:
    """Parse a single Markdown file with YAML frontmatter into a :class:`Document`."""
    raw = path.read_text(encoding="utf-8")
    match = _FRONTMATTER.match(raw)
    if match is None:
        raise ValueError(f"{path} is missing YAML frontmatter (--- ... ---)")
    meta = yaml.safe_load(match.group(1)) or {}
    if not isinstance(meta, dict):
        raise ValueError(f"{path} frontmatter must be a YAML mapping")
    body = match.group(2).strip()

    required = ("doc_id", "tenant", "classification", "title")
    missing = [k for k in required if k not in meta]
    if missing:
        raise ValueError(f"{path} frontmatter missing keys: {', '.join(missing)}")

    flags = {k: bool(v) for k, v in meta.items() if isinstance(v, bool)}
    return Document(
        doc_id=str(meta["doc_id"]),
        tenant=str(meta["tenant"]),
        classification=Classification(str(meta["classification"])),
        title=str(meta["title"]),
        text=body,
        path=path,
        flags=flags,
    )


def load_corpus(tenants_dir: Path = TENANTS_DIR) -> list[Document]:
    """Load every tenant document under ``tenants_dir``, sorted by path.

    Sorting by path makes the load order deterministic, so downstream chunking
    and embedding produce stable ids across runs.
    """
    paths = sorted(tenants_dir.glob("*/docs/*.md"))
    return [parse_document(p) for p in paths]


__all__ = ["TENANTS_DIR", "Document", "load_corpus", "parse_document"]
