import { describe, expect, it } from "vitest";

import type { GuardedContext, RetrievedChunk } from "@/api/types";
import {
  classificationClass,
  enrich,
  evidenceFlow,
  groupByDocument,
  isContained,
  outcomeClass,
  tally,
  tokenReduction,
} from "@/lib/firewall";

function retrieved(): RetrievedChunk[] {
  return [
    { id: "c1", doc_id: "doc-a", tenant: "acme", classification: "public", text: "hello", score: 0.9, metadata: {} },
    { id: "c2", doc_id: "doc-a", tenant: "acme", classification: "confidential", text: "secret", score: 0.5, metadata: {} },
    { id: "c3", doc_id: "doc-b", tenant: "acme", classification: "internal", text: "pii here", score: 0.7, metadata: {} },
  ];
}

function guarded(): GuardedContext {
  return {
    allowed_chunks: [
      { id: "c1", doc_id: "doc-a", tenant: "acme", classification: "public", text: "hello", metadata: {}, pii_spans: [], secret_spans: [], risk_signals: [] },
      { id: "c3", doc_id: "doc-b", tenant: "acme", classification: "internal", text: "***", metadata: {}, pii_spans: [], secret_spans: [], risk_signals: [] },
    ],
    decisions: [
      { chunk_id: "c1", outcome: "allowed", reasons: [], policies_triggered: [] },
      { chunk_id: "c2", outcome: "blocked", reasons: ["confidential"], policies_triggered: ["sales-no-confidential"] },
      { chunk_id: "c3", outcome: "redacted", reasons: ["pii"], policies_triggered: ["redact-pii"] },
    ],
    tokens_before: 100,
    tokens_after: 60,
  };
}

describe("tally", () => {
  it("counts each outcome", () => {
    expect(tally(guarded())).toEqual({ allowed: 1, blocked: 1, redacted: 1 });
  });
});

describe("tokenReduction", () => {
  it("returns the percent of tokens removed", () => {
    expect(tokenReduction(guarded())).toBe(40);
  });

  it("is zero when nothing was measured", () => {
    expect(tokenReduction({ allowed_chunks: [], decisions: [], tokens_before: 0, tokens_after: 0 })).toBe(0);
  });
});

describe("isContained", () => {
  it("is true when the firewall withheld a chunk", () => {
    expect(isContained(guarded())).toBe(true);
  });
});

describe("outcomeClass", () => {
  it("maps outcomes to tag modifiers", () => {
    expect(outcomeClass("allowed")).toBe("tag tag--allowed");
    expect(outcomeClass("blocked")).toBe("tag tag--blocked");
    expect(outcomeClass("redacted")).toBe("tag tag--redacted");
  });
});

describe("classificationClass", () => {
  it("treats confidential as blocked-style", () => {
    expect(classificationClass("confidential")).toBe("tag tag--blocked");
    expect(classificationClass("public")).toBe("tag tag--allowed");
  });
});

describe("enrich", () => {
  it("joins hits with their verdict and prompt membership", () => {
    const enriched = enrich(retrieved(), guarded());
    const blocked = enriched.find((c) => c.id === "c2")!;
    expect(blocked.outcome).toBe("blocked");
    expect(blocked.inPrompt).toBe(false);
    expect(blocked.policies).toContain("sales-no-confidential");

    const redacted = enriched.find((c) => c.id === "c3")!;
    expect(redacted.inPrompt).toBe(true);
  });
});

describe("groupByDocument", () => {
  it("groups chunks by source document, best score first", () => {
    const groups = groupByDocument(enrich(retrieved(), guarded()));
    expect(groups.map((g) => g.docId)).toEqual(["doc-a", "doc-b"]);
    const docA = groups[0];
    expect(docA.chunks).toHaveLength(2);
    expect(docA.anyInPrompt).toBe(true);
    expect(docA.anyWithheld).toBe(true);
  });
});

describe("evidenceFlow", () => {
  it("renders a mermaid flowchart with the counts", () => {
    const flow = evidenceFlow(3, guarded());
    expect(flow.startsWith("flowchart LR")).toBe(true);
    expect(flow).toContain("Retrieved<br/>3");
  });
});
