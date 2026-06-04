// Corpus drawer logic: drives the in-Console "Documents & attacks" panel.
// Reads the static corpus + attack catalog, groups documents by tenant, tracks
// which tab/document is selected, and shapes the per-identity access matrix.
// The SFC only renders what this returns (Vue rule #1).
import { computed, ref } from "vue";

import {
  accessMatrix,
  ATTACK_CATEGORY_LABELS,
  ATTACK_PROMPTS,
  CORPUS_DOCUMENTS,
  groupCorpusByTenant,
  type AttackCategory,
  type AttackPrompt,
  type CorpusDocument,
} from "@/lib/corpus";
import { DEMO_IDENTITIES } from "@/lib/identities";
import { useAuthStore } from "@/stores/auth";

export type CorpusTab = "documents" | "attacks";

export interface AttackGroup {
  category: AttackCategory;
  label: string;
  prompts: AttackPrompt[];
}

export function useCorpusDrawer() {
  const auth = useAuthStore();
  const tab = ref<CorpusTab>("documents");
  const selectedDocId = ref<string>(CORPUS_DOCUMENTS[0]?.docId ?? "");

  const tenantGroups = computed(() => groupCorpusByTenant(CORPUS_DOCUMENTS));

  const selectedDocument = computed<CorpusDocument | null>(
    () => CORPUS_DOCUMENTS.find((doc) => doc.docId === selectedDocId.value) ?? null,
  );

  const selectedAccess = computed(() =>
    selectedDocument.value ? accessMatrix(selectedDocument.value) : [],
  );

  const activeIdentity = computed(
    () => DEMO_IDENTITIES.find((identity) => identity.sub === auth.activeSub) ?? DEMO_IDENTITIES[0],
  );

  const identityAttackPrompts = computed(() =>
    ATTACK_PROMPTS.filter((prompt) => prompt.sub === activeIdentity.value?.sub),
  );

  const attackGroups = computed<AttackGroup[]>(() => {
    const order: AttackCategory[] = ["confidential", "cross-tenant", "pii", "injection", "baseline"];
    return order
      .map((category) => ({
        category,
        label: ATTACK_CATEGORY_LABELS[category],
        prompts: identityAttackPrompts.value.filter((prompt) => prompt.category === category),
      }))
      .filter((group) => group.prompts.length > 0);
  });

  function showTab(next: CorpusTab): void {
    tab.value = next;
  }

  function selectDocument(docId: string): void {
    selectedDocId.value = docId;
  }

  return {
    tab,
    selectedDocId,
    tenantGroups,
    selectedDocument,
    selectedAccess,
    activeIdentity,
    identityAttackPrompts,
    attackGroups,
    showTab,
    selectDocument,
  };
}
