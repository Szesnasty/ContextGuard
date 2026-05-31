"""`make red-team` — regenerate RED-TEAM.md (Milestone B5.2).

Thin wrapper around :func:`contextguard_eval_harness.red_team_runner.main` so the
build-plan verb has a stable home under ``scripts/``.
"""

from __future__ import annotations

from contextguard_eval_harness.red_team_runner import main

if __name__ == "__main__":
    main()
