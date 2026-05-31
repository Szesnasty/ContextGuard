// History store: an in-memory log of guarded runs from the Query Console. The
// Evidence Viewer reads from here so an operator can re-open any past query and
// inspect its firewall decisions, token deltas, and before/after context. Kept
// client-side (the API exposes no evidence-by-id endpoint yet); newest first,
// capped so the demo never grows unbounded.
import { defineStore } from "pinia";
import { computed, ref } from "vue";

import type { GuardedContext, RetrievedChunk } from "@/api/types";

export interface RunRecord {
  id: string;
  query: string;
  identity: string;
  createdAt: string;
  /** What retrieval returned (the pre-firewall, potentially leaky context). */
  retrieved: RetrievedChunk[];
  /** The firewall's verdict over those chunks. */
  guarded: GuardedContext;
  /** The model's answer from /v1/query, when it ran. */
  answer: string | null;
}

const MAX_RUNS = 25;

export const useHistoryStore = defineStore("history", () => {
  const runs = ref<RunRecord[]>([]);
  const selectedId = ref<string | null>(null);

  const selected = computed(() => runs.value.find((r) => r.id === selectedId.value) ?? null);

  function record(run: Omit<RunRecord, "id" | "createdAt">): RunRecord {
    const entry: RunRecord = {
      ...run,
      id: crypto.randomUUID(),
      createdAt: new Date().toISOString(),
    };
    runs.value = [entry, ...runs.value].slice(0, MAX_RUNS);
    selectedId.value = entry.id;
    return entry;
  }

  function select(id: string): void {
    selectedId.value = id;
  }

  return { runs, selectedId, selected, record, select };
});
