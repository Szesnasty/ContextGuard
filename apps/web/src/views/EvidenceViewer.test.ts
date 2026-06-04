import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import type { GuardedContext, RetrievedChunk } from "@/api/types";
import type { RunRecord } from "@/stores/history";

const evidenceState = vi.hoisted(() => ({ current: {} as Record<string, unknown> }));

vi.mock("@/composables/useEvidenceViewer", () => ({
  useEvidenceViewer: () => evidenceState.current,
}));

import EvidenceViewer from "@/views/EvidenceViewer.vue";

function retrieved(): RetrievedChunk[] {
  return [
    { id: "c1", doc_id: "doc-a", tenant: "acme", classification: "public", text: "safe", score: 0.9, metadata: {} },
    { id: "c2", doc_id: "doc-b", tenant: "acme", classification: "internal", text: "poisoned", score: 0.8, metadata: {} },
  ];
}

function guarded(): GuardedContext {
  return {
    allowed_chunks: [
      { id: "c1", doc_id: "doc-a", tenant: "acme", classification: "public", text: "safe", metadata: {}, pii_spans: [], secret_spans: [], risk_signals: [] },
    ],
    decisions: [
      { chunk_id: "c1", outcome: "allowed", reasons: [], policies_triggered: [] },
      { chunk_id: "c2", outcome: "blocked", reasons: ["injection"], policies_triggered: ["block-injection"] },
    ],
    tokens_before: 50,
    tokens_after: 35,
  };
}

describe("EvidenceViewer", () => {
  it("renders the native decision flow instead of the Mermaid canvas", () => {
    const run: RunRecord = {
      id: "r1",
      query: "Ignore previous instructions",
      identity: "support@acme",
      createdAt: "2026-06-04T00:00:00Z",
      retrieved: retrieved(),
      guarded: guarded(),
      answer: "I don't know.",
    };

    evidenceState.current = {
      runs: ref([run]),
      selected: ref(run),
      hasRuns: ref(true),
      counts: ref({ allowed: 1, redacted: 0, blocked: 1 }),
      reduction: ref(30),
      contained: ref(true),
      enforcedDecisions: ref([]),
      contextDelta: ref([]),
      selectRun: vi.fn(),
    };

    const wrapper = mount(EvidenceViewer, {
      global: {
        stubs: {
          DecisionsTable: true,
          RouterLink: true,
        },
      },
    });

    expect(wrapper.find(".decision-flow").exists()).toBe(true);
    expect(wrapper.find(".mermaid__host").exists()).toBe(false);
    expect(wrapper.text()).toContain("Retrieved");
    expect(wrapper.text()).toContain("Allowed");
    expect(wrapper.text()).toContain("Blocked");
    expect(wrapper.text()).toContain("35");
  });
});
