import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import type { GuardedContext, RetrievedChunk } from "@/api/types";
import type { ConsoleRun } from "@/composables/useQueryConsole";

const consoleState = vi.hoisted(() => ({ current: {} as Record<string, unknown> }));

vi.mock("@/composables/useQueryConsole", () => ({
  useQueryConsole: () => consoleState.current,
}));

import QueryConsole from "@/views/QueryConsole.vue";

function retrieved(): RetrievedChunk[] {
  return [
    {
      id: "c1",
      doc_id: "doc-a",
      tenant: "acme",
      classification: "public",
      text: "Safe source text.",
      score: 0.9,
      metadata: {},
    },
  ];
}

function guarded(): GuardedContext {
  return {
    allowed_chunks: [
      {
        id: "c1",
        doc_id: "doc-a",
        tenant: "acme",
        classification: "public",
        text: "Safe source text.",
        metadata: {},
        pii_spans: [],
        secret_spans: [],
        risk_signals: [],
      },
    ],
    decisions: [{ chunk_id: "c1", outcome: "allowed", reasons: [], policies_triggered: [] }],
    tokens_before: 20,
    tokens_after: 20,
  };
}

beforeEach(() => {
  consoleState.current = {};
});

describe("QueryConsole", () => {
  it("wires the source button to the selected run", async () => {
    const run: ConsoleRun = {
      query: "What happened?",
      retrieved: retrieved(),
      guarded: guarded(),
    };
    const openDrawer = vi.fn();

    consoleState.current = {
      input: ref(""),
      k: ref(5),
      messages: ref([{ id: "m1", role: "assistant" as const, text: "Answer", run }]),
      error: ref(null),
      isSending: ref(false),
      drawerOpen: ref(false),
      drawerRun: ref(null),
      corpusOpen: ref(false),
      emptyGuard: guarded(),
      send: vi.fn(),
      openDrawer,
      closeDrawer: vi.fn(),
      openCorpus: vi.fn(),
      closeCorpus: vi.fn(),
      loadAttack: vi.fn(),
    };

    const wrapper = mount(QueryConsole, {
      global: {
        stubs: {
          CorpusDrawer: true,
          IdentityPicker: true,
          ModelPicker: true,
          RagDrawer: true,
        },
      },
    });

    const button = wrapper.get(".bubble__open");
    expect(button.attributes("type")).toBe("button");

    await button.trigger("click");

    expect(openDrawer).toHaveBeenCalledOnce();
    expect(openDrawer).toHaveBeenCalledWith(run);
  });
});
