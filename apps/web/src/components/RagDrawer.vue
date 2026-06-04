<script setup lang="ts">
import { toRef } from "vue";

import type { GuardedContext, RetrievedChunk } from "@/api/types";
import SanitizedHtml from "@/components/SanitizedHtml";
import { useRagDrawer } from "@/composables/useRagDrawer";
import { classificationClass, outcomeClass, renderMd } from "@/lib/firewall";

const props = defineProps<{
  open: boolean;
  query: string;
  retrieved: RetrievedChunk[];
  guarded: GuardedContext;
}>();

const emit = defineEmits<{ close: [] }>();

const { documents, selectedDocument, inPromptCount, withheldCount, selectDocument, scorePercent } =
  useRagDrawer(toRef(props, "retrieved"), toRef(props, "guarded"));
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="drawer__scrim"
      @click="emit('close')"
    />
    <aside
      class="drawer"
      :class="{ 'drawer--open': open }"
      aria-label="RAG sources and evidence"
    >
      <header class="drawer__head">
        <div>
          <strong>Sources &amp; evidence</strong>
          <div class="drawer__query">
            “{{ query }}”
          </div>
        </div>
        <button
          class="ghost"
          @click="emit('close')"
        >
          Close ✕
        </button>
      </header>

      <div class="drawer__stats">
        <div class="stat">
          <span class="stat__n">{{ documents.length }}</span><span class="stat__k">documents</span>
        </div>
        <div class="stat">
          <span class="stat__n">{{ retrieved.length }}</span><span class="stat__k">chunks</span>
        </div>
        <div class="stat">
          <span class="stat__n">{{ inPromptCount }}</span><span class="stat__k">in prompt</span>
        </div>
        <div class="stat">
          <span class="stat__n">{{ withheldCount }}</span><span class="stat__k">withheld</span>
        </div>
      </div>

      <p class="drawer__hint muted">
        These are the documents retrieval pulled for this query. Switch identity and re-run to watch
        the same document flip between <em>used here</em> and <em>withheld</em> — the verdict comes
        from the policy, per identity.
      </p>

      <div class="drawer__body">
        <nav class="sources">
          <button
            v-for="document in documents"
            :key="document.docId"
            class="sources__item"
            :class="{ 'sources__item--active': document.docId === selectedDocument?.docId }"
            @click="selectDocument(document.docId)"
          >
            <div class="sources__title">
              <code>{{ document.docId }}</code>
            </div>
            <div class="sources__meta">
              <span :class="classificationClass(document.classification)">{{ document.classification }}</span>
              <span class="muted">{{ document.tenant }}</span>
            </div>
            <div class="sources__flags">
              <span
                v-if="document.anyInPrompt"
                class="tag tag--allowed"
              >used</span>
              <span
                v-if="document.anyWithheld"
                class="tag tag--blocked"
              >withheld</span>
              <span class="sources__count muted">{{ document.chunks.length }} chunk(s)</span>
            </div>
          </button>
          <p
            v-if="!documents.length"
            class="sources__empty muted"
          >
            No sources yet — run a query in the console.
          </p>
        </nav>

        <section
          v-if="selectedDocument"
          class="detail"
        >
          <header class="detail__head">
            <h3 class="detail__title">
              <code>{{ selectedDocument.docId }}</code>
            </h3>
            <div class="detail__badges">
              <span :class="classificationClass(selectedDocument.classification)">{{
                selectedDocument.classification
              }}</span>
              <span class="muted">tenant: {{ selectedDocument.tenant }}</span>
            </div>
          </header>

          <article
            v-for="chunk in selectedDocument.chunks"
            :key="chunk.id"
            class="passage"
            :class="`passage--${chunk.outcome}`"
          >
            <div class="passage__bar">
              <span :class="outcomeClass(chunk.outcome)">{{ chunk.outcome }}</span>
              <code class="muted">{{ chunk.id }}</code>
              <span
                class="passage__score"
                :title="`relevance ${chunk.score.toFixed(3)}`"
              >
                <span
                  class="passage__score-fill"
                  :style="{ width: scorePercent(chunk.score) + '%' }"
                />
              </span>
              <span
                v-if="chunk.inPrompt"
                class="passage__note"
              >→ in prompt</span>
              <span
                v-else
                class="passage__note"
              >✕ not sent to model</span>
            </div>
            <SanitizedHtml
              class="passage__text"
              :html="renderMd(chunk.text)"
            />
            <div
              v-if="chunk.reasons.length || chunk.policies.length"
              class="passage__why muted"
            >
              <span v-if="chunk.policies.length">policy: {{ chunk.policies.join(", ") }}</span>
              <span v-if="chunk.reasons.length"> — {{ chunk.reasons.join("; ") }}</span>
            </div>
          </article>
        </section>
      </div>
    </aside>
  </Teleport>
</template>

<style scoped lang="scss">
@use "@/styles/tokens" as *;

.drawer {
  position: fixed;
  top: 0;
  right: 0;
  height: 100%;
  width: min(820px, 92vw);
  background: $bg-elev;
  border-left: 1px solid $border;
  z-index: 50;
  display: flex;
  flex-direction: column;
  transform: translateX(100%);
  transition: transform 0.18s ease-out;

  &--open {
    transform: translateX(0);
  }

  &__scrim {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    z-index: 40;
  }

  &__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid $border;
  }

  &__query {
    font-size: 12px;
    color: $text-dim;
  }

  &__stats {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    padding: 0.75rem 1rem;
  }

  &__hint {
    margin: 0;
    padding: 0 1rem 0.75rem;
    font-size: 12px;
  }

  &__body {
    flex: 1;
    display: grid;
    grid-template-columns: 240px 1fr;
    min-height: 0;
  }
}

.sources {
  border-right: 1px solid $border;
  overflow: auto;
  display: flex;
  flex-direction: column;

  &__item {
    text-align: left;
    background: transparent;
    color: $text;
    border: none;
    border-bottom: 1px solid $border;
    border-radius: 0;
    padding: 0.6rem 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    cursor: pointer;

    &:hover {
      background: $bg-elev-2;
    }

    &--active {
      background: $bg-elev-2;
      box-shadow: inset 3px 0 0 $accent;
    }
  }

  &__meta,
  &__flags {
    display: flex;
    gap: 0.4rem;
    align-items: center;
    flex-wrap: wrap;
  }

  &__count {
    font-size: 11px;
  }

  &__empty {
    padding: 0.75rem;
  }
}

.detail {
  overflow: auto;
  padding: 1rem;

  &__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1rem;
  }

  &__title {
    margin: 0;
  }

  &__badges {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }
}

.passage {
  border: 1px solid $border;
  border-left-width: 4px;
  border-radius: $radius;
  padding: 0.6rem 0.8rem;
  margin-bottom: 0.75rem;
  background: $bg;

  &--allowed {
    border-left-color: $allowed;
  }

  &--redacted {
    border-left-color: $redacted;
  }

  &--blocked {
    border-left-color: $blocked;
    opacity: 0.85;

    .passage__text {
      text-decoration: line-through;
      color: $text-dim;
    }
  }

  &__bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.4rem;
  }

  &__text {
    margin: 0;

    :deep(p) { margin: 0 0 0.35rem; }
    :deep(ul) { margin: 0 0 0.35rem; padding-left: 1.2em; }
    :deep(li) { margin: 0.15rem 0; }
    :deep(h3), :deep(h4), :deep(h5) { margin: 0 0 0.25rem; font-size: 0.95em; }
  }

  &__why {
    margin-top: 0.4rem;
    font-size: 12px;
  }

  &__note {
    font-size: 11px;
    color: $text-dim;
  }

  &__score {
    display: inline-block;
    width: 80px;
    height: 6px;
    background: $border;
    border-radius: 999px;
    overflow: hidden;
  }

  &__score-fill {
    display: block;
    height: 100%;
    background: $accent;
  }
}
</style>
