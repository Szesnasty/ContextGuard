// Query Console logic: a chat-style RAG session. Each send runs the leaky
// /v1/query (retrieval + model answer), then /v1/guard to get the firewall
// verdict over the retrieved chunks, records both in history, and exposes the
// run so the evidence drawer can browse its sources. The SFC stays presentational.
import { ref } from "vue";

import type { GuardedContext, RetrievedChunk } from "@/api/types";
import { guardChunks, retrievedToChunk, runQuery } from "@/api/operations";
import type { AttackPrompt } from "@/lib/corpus";
import { useAuthStore } from "@/stores/auth";
import { useHistoryStore } from "@/stores/history";

export interface ConsoleRun {
  query: string;
  retrieved: RetrievedChunk[];
  guarded: GuardedContext;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  run: ConsoleRun | null;
}

const EMPTY_GUARD: GuardedContext = {
  allowed_chunks: [],
  decisions: [],
  tokens_before: 0,
  tokens_after: 0,
};

export function useQueryConsole() {
  const auth = useAuthStore();
  const history = useHistoryStore();

  const input = ref("");
  const k = ref(5);
  const messages = ref<ChatMessage[]>([]);
  const error = ref<string | null>(null);
  const isSending = ref(false);
  const drawerOpen = ref(false);
  const drawerRun = ref<ConsoleRun | null>(null);
  const corpusOpen = ref(false);

  function pushMessage(role: ChatMessage["role"], text: string, run: ConsoleRun | null): void {
    messages.value.push({ id: crypto.randomUUID(), role, text, run });
  }

  async function send(): Promise<void> {
    if (isSending.value) return;

    const query = input.value.trim();
    if (!query) return;

    if (!auth.isAuthenticated) {
      error.value = "Set a token first — pick an identity and paste its token above.";
      return;
    }

    error.value = null;
    isSending.value = true;
    pushMessage("user", query, null);
    input.value = "";

    try {
      const result = await runQuery(query, k.value);
      const guarded = await guardChunks(query, result.retrieved_chunks.map(retrievedToChunk));
      const run: ConsoleRun = { query, retrieved: result.retrieved_chunks, guarded };

      history.record({
        query,
        identity: auth.label,
        retrieved: result.retrieved_chunks,
        guarded,
        answer: result.answer,
      });

      pushMessage("assistant", result.answer, run);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : String(cause);
      error.value = message;
      pushMessage("assistant", `⚠️ ${message}`, null);
    } finally {
      isSending.value = false;
    }
  }

  function openDrawer(run: ConsoleRun): void {
    drawerRun.value = run;
    drawerOpen.value = true;
  }

  function closeDrawer(): void {
    drawerOpen.value = false;
  }

  function openCorpus(): void {
    corpusOpen.value = true;
  }

  function closeCorpus(): void {
    corpusOpen.value = false;
  }

  // Load a planted attack: select the identity it targets, drop its text in the
  // composer, and close the drawer so the operator just hits Send.
  function loadAttack(attack: AttackPrompt): void {
    auth.selectIdentity(attack.sub);
    input.value = attack.prompt;
    corpusOpen.value = false;
  }

  return {
    auth,
    input,
    k,
    messages,
    error,
    isSending,
    drawerOpen,
    drawerRun,
    corpusOpen,
    emptyGuard: EMPTY_GUARD,
    send,
    openDrawer,
    closeDrawer,
    openCorpus,
    closeCorpus,
    loadAttack,
  };
}
