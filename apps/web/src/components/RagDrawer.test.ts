import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";

import type { GuardedContext, RetrievedChunk } from "@/api/types";
import RagDrawer from "@/components/RagDrawer.vue";

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

afterEach(() => {
  document.body.innerHTML = "";
});

describe("RagDrawer", () => {
  it("does not leave a closed drawer mounted in the document body", async () => {
    mount(RagDrawer, {
      attachTo: document.body,
      props: {
        open: false,
        query: "What happened?",
        retrieved: retrieved(),
        guarded: guarded(),
      },
    });

    await nextTick();

    expect(document.body.textContent).not.toContain("Sources & evidence");
    expect(document.querySelector(".drawer")).toBeNull();
  });

  it("renders sources when opened and emits close", async () => {
    const wrapper = mount(RagDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        query: "What happened?",
        retrieved: retrieved(),
        guarded: guarded(),
      },
    });

    await nextTick();

    expect(document.body.textContent).toContain("Sources & evidence");
    expect(document.body.textContent).toContain("doc-a");

    const close = document.querySelector(".drawer button") as HTMLButtonElement | null;
    expect(close).not.toBeNull();
    close?.click();
    await nextTick();

    expect(wrapper.emitted("close")).toHaveLength(1);
  });
});
