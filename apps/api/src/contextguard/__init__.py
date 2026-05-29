"""ContextGuard — policy-aware context firewall for production RAG.

This is the application/runtime package. The zero-infra decision core lives in
`contextguard.core` and must not import anything heavier than pydantic+pyyaml
(ADR-004, ADR-010); heavier subpackages (retrieval, llm, db, …) are wired in by
later phases and loaded lazily.
"""

__version__ = "0.0.0"
