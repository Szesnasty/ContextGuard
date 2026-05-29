"""`make benchmark` — regenerate BENCHMARK.md (Milestone A5).

Thin wrapper around :func:`contextguard_eval_harness.benchmark.main` so the
build-plan verb has a stable home under ``scripts/``.
"""

from __future__ import annotations

from contextguard_eval_harness.benchmark import main

if __name__ == "__main__":
    main()
