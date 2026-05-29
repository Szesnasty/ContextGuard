"""`make leak-demo` — print the before/after leak report (Milestone A5).

Runs the headline scenarios through a naive (no-policy) `ContextGuard` and the
policy-protected one, and prints a readable, screenshot-able report showing the
confidential/cross-tenant content reaching the model with the policy off and
being contained with it on. Zero infra: no Docker, no network, no models.
"""

from __future__ import annotations

from contextguard_eval_harness.benchmark import DEFAULT_POLICY
from contextguard_eval_harness.scenarios import SCENARIOS, Scenario

from contextguard import ContextGuard


def _report(scenario: Scenario, guard_off: ContextGuard, guard_on: ContextGuard) -> None:
    off = guard_off.guard(scenario.user, scenario.title, list(scenario.chunks))
    on = guard_on.guard(scenario.user, scenario.title, list(scenario.chunks))
    off_text = "\n".join(c.text for c in off.allowed_chunks)
    on_text = "\n".join(c.text for c in on.allowed_chunks)
    leaked_off = scenario.sensitive_marker in off_text
    leaked_on = scenario.sensitive_marker in on_text

    print(f"\n=== {scenario.title} ===")
    print(f"user: {scenario.user.role}@{scenario.user.tenant}")
    print(f"sensitive marker: {scenario.sensitive_marker!r}")
    print(
        f"  policy OFF -> {'LEAK' if leaked_off else 'clean'} "
        f"({len(off.allowed_chunks)} chunks reach the model)"
    )
    print(
        f"  policy ON  -> {'LEAK' if leaked_on else 'contained'} "
        f"({len(on.allowed_chunks)} chunks reach the model)"
    )
    for decision in on.decisions:
        print(
            f"    - {decision.chunk_id}: {decision.outcome.value}"
            + (
                f" [{', '.join(decision.policies_triggered)}]"
                if decision.policies_triggered
                else ""
            )
        )


def main() -> None:
    guard_off = ContextGuard()
    guard_on = ContextGuard.from_policy(DEFAULT_POLICY)
    print("ContextGuard leak demo — naive RAG (policy off) vs. firewall (policy on)")
    for scenario in SCENARIOS:
        _report(scenario, guard_off, guard_on)
    print("\nRun `make benchmark` to regenerate BENCHMARK.md with the aggregate rates.")


if __name__ == "__main__":
    main()
