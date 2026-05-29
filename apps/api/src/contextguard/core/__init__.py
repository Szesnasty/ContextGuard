"""Zero-infra decision core (ADR-004, ADR-010).

Pure, deterministic, in-memory. MUST NOT import anything heavier than
`pydantic` + `pyyaml`. No DB, no network, no models. Filled in phase 1.
"""
