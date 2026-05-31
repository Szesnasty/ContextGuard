// Drawer logic: turn this query's retrieval hits + firewall verdict into a
// document-grouped, selectable source list (NotebookLM-style evidence). The SFC
// only renders what this returns.
import { computed, ref, watch, type Ref } from "vue";

import type { GuardedContext, RetrievedChunk } from "@/api/types";
import { enrich, groupByDocument, type DocumentGroup } from "@/lib/firewall";

export function useRagDrawer(retrieved: Ref<RetrievedChunk[]>, guarded: Ref<GuardedContext>) {
  const selectedDocId = ref<string | null>(null);

  const enrichedChunks = computed(() => enrich(retrieved.value, guarded.value));
  const documents = computed<DocumentGroup[]>(() => groupByDocument(enrichedChunks.value));
  const selectedDocument = computed(
    () =>
      documents.value.find((document) => document.docId === selectedDocId.value) ??
      documents.value[0] ??
      null,
  );
  const inPromptCount = computed(
    () => enrichedChunks.value.filter((chunk) => chunk.inPrompt).length,
  );
  const withheldCount = computed(() => retrieved.value.length - inPromptCount.value);

  // Keep a valid selection as the source set changes; default to top-ranked.
  watch(
    documents,
    (list) => {
      if (list.find((document) => document.docId === selectedDocId.value)) return;
      selectedDocId.value = list[0]?.docId ?? null;
    },
    { immediate: true },
  );

  function selectDocument(docId: string) {
    selectedDocId.value = docId;
  }

  function scorePercent(score: number): number {
    return Math.max(2, Math.min(100, Math.round(score * 100)));
  }

  return {
    documents,
    selectedDocument,
    inPromptCount,
    withheldCount,
    selectDocument,
    scorePercent,
  };
}
