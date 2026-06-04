<script setup lang="ts">
import type { AttackPrompt } from "@/lib/corpus";
import SanitizedHtml from "@/components/SanitizedHtml";
import { useCorpusDrawer } from "@/composables/useCorpusDrawer";
import { classificationClass, outcomeClass, renderMd } from "@/lib/firewall";

defineProps<{ open: boolean }>();

const emit = defineEmits<{ close: []; load: [attack: AttackPrompt] }>();

const {
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
} = useCorpusDrawer();

function expectedLabel(expected: AttackPrompt["expected"]): string {
  if (expected === "blocked") return "expect source blocked";
  if (expected === "redacted") return "expect PII masked";
  return "expect allowed";
}
</script>

<template>
  <Teleport
    v-if="open"
    to="body"
  >
    <div
      class="corpus__scrim"
      @click="emit('close')"
    />
    <aside
      class="corpus corpus--open"
      aria-label="Corpus documents and attack prompts"
    >
      <header class="corpus__head">
        <div>
          <strong>Documents &amp; attacks</strong>
          <div class="corpus__sub muted">
            Read the seed corpus, see who the firewall lets near each document, and load a planted
            attack into the chat.
          </div>
        </div>
        <button
          class="ghost corpus__close"
          type="button"
          aria-label="Close documents and attacks"
          @click="emit('close')"
        >
          <span>Close</span>
          <svg
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path d="M6 6l12 12" />
            <path d="M18 6L6 18" />
          </svg>
        </button>
      </header>

      <nav class="corpus__tabs">
        <button
          class="corpus__tab"
          :class="{ 'corpus__tab--active': tab === 'documents' }"
          @click="showTab('documents')"
        >
          Documents
        </button>
        <button
          class="corpus__tab"
          :class="{ 'corpus__tab--active': tab === 'attacks' }"
          @click="showTab('attacks')"
        >
          Attack prompts
        </button>
      </nav>

      <!-- Documents tab -->
      <div
        v-if="tab === 'documents'"
        class="corpus__body"
      >
        <nav class="tree">
          <div
            v-for="group in tenantGroups"
            :key="group.tenant"
            class="tree__group"
          >
            <div class="tree__tenant">
              tenant: <code>{{ group.tenant }}</code>
            </div>
            <button
              v-for="document in group.documents"
              :key="document.docId"
              class="tree__item"
              :class="{ 'tree__item--active': document.docId === selectedDocId }"
              @click="selectDocument(document.docId)"
            >
              <span class="tree__title">{{ document.title }}</span>
              <span class="tree__meta">
                <span :class="classificationClass(document.classification)">{{
                  document.classification
                }}</span>
                <span
                  v-for="docTag in document.tags"
                  :key="docTag.kind"
                  class="tag tag--blocked"
                >{{ docTag.label }}</span>
              </span>
            </button>
          </div>
        </nav>

        <section
          v-if="selectedDocument"
          class="detail"
        >
          <header class="detail__head">
            <h3 class="detail__title">
              {{ selectedDocument.title }}
            </h3>
            <code class="muted">{{ selectedDocument.docId }}</code>
          </header>

          <div class="detail__badges">
            <span :class="classificationClass(selectedDocument.classification)">{{
              selectedDocument.classification
            }}</span>
            <span class="muted">tenant: {{ selectedDocument.tenant }}</span>
            <span
              v-for="docTag in selectedDocument.tags"
              :key="docTag.kind"
              class="tag tag--blocked"
            >{{ docTag.label }}</span>
          </div>

          <SanitizedHtml
            class="detail__summary"
            :html="renderMd(selectedDocument.summary)"
          />

          <div class="detail__access">
            <h4 class="detail__h4">
              Who it’s for
            </h4>
            <SanitizedHtml
              class="muted detail__note"
              :html="renderMd(selectedDocument.accessNote)"
            />
          </div>

          <div class="detail__matrix">
            <h4 class="detail__h4">
              Firewall verdict per identity
            </h4>
            <div
              v-for="row in selectedAccess"
              :key="row.identity.sub"
              class="matrix__row"
            >
              <span class="matrix__id">
                <code>{{ row.identity.sub }}</code>
                <span class="muted">{{ row.identity.role }} @ {{ row.identity.tenant }}</span>
              </span>
              <span :class="outcomeClass(row.outcome)">{{ row.outcome }}</span>
            </div>
          </div>
        </section>
      </div>

      <!-- Attacks tab -->
      <div
        v-else
        class="corpus__body corpus__body--single"
      >
        <div class="attacks">
          <div class="attacks__intro">
            <div>
              <span class="attacks__eyebrow">Prompt set</span>
              <strong>{{ activeIdentity?.sub }}</strong>
              <span class="muted"> · {{ activeIdentity?.role }} @ {{ activeIdentity?.tenant }}</span>
            </div>
            <span class="tag tag--allowed">{{ identityAttackPrompts.length }} prompts</span>
          </div>
          <section
            v-for="group in attackGroups"
            :key="group.category"
            class="attacks__group"
          >
            <h4 class="attacks__label">
              {{ group.label }}
            </h4>
            <article
              v-for="attack in group.prompts"
              :key="attack.id"
              class="probe"
            >
              <div class="probe__head">
                <span class="probe__title">{{ attack.title }}</span>
                <span :class="outcomeClass(attack.expected)">{{ expectedLabel(attack.expected) }}</span>
              </div>
              <p class="probe__prompt">
                “{{ attack.prompt }}”
              </p>
              <p class="probe__why muted">
                <SanitizedHtml
                  tag="span"
                  :html="renderMd(attack.rationale)"
                />
              </p>
              <button
                class="probe__load"
                @click="emit('load', attack)"
              >
                Load to chat →
              </button>
            </article>
          </section>
          <p
            v-if="!attackGroups.length"
            class="attacks__empty muted"
          >
            No attack prompts for this identity yet.
          </p>
        </div>
      </div>
    </aside>
  </Teleport>
</template>

<style scoped lang="scss">
@use "@/styles/tokens" as *;

.corpus {
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
    gap: 1rem;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid $border;
  }

  &__sub {
    font-size: 12px;
    margin-top: 0.2rem;
    max-width: 56ch;
  }

  &__close {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    white-space: nowrap;

    svg {
      width: 16px;
      height: 16px;
      fill: none;
      stroke: currentColor;
      stroke-linecap: round;
      stroke-width: 2;
    }
  }

  &__tabs {
    display: flex;
    gap: 0.25rem;
    padding: 0.5rem 1rem 0;
    border-bottom: 1px solid $border;
  }

  &__tab {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    color: $text-dim;
    padding: 0.4rem 0.6rem;
    cursor: pointer;

    &--active {
      color: $text;
      border-bottom-color: $accent;
    }
  }

  &__body {
    flex: 1;
    display: grid;
    grid-template-columns: 280px 1fr;
    min-height: 0;

    &--single {
      grid-template-columns: 1fr;
    }
  }
}

.tree {
  border-right: 1px solid $border;
  overflow: auto;

  &__group {
    border-bottom: 1px solid $border;
  }

  &__tenant {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: $text-dim;
    padding: 0.5rem 0.75rem 0.3rem;
  }

  &__item {
    text-align: left;
    width: 100%;
    background: transparent;
    color: $text;
    border: none;
    border-radius: 0;
    padding: 0.5rem 0.75rem;
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

  &__title {
    font-size: 13px;
  }

  &__meta {
    display: flex;
    gap: 0.3rem;
    flex-wrap: wrap;
    align-items: center;
  }
}

.detail {
  overflow: auto;
  padding: 1rem;

  &__head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 1rem;
  }

  &__title {
    margin: 0 0 0.25rem;
  }

  &__badges {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
    align-items: center;
    margin: 0.5rem 0 0.75rem;
  }

  &__summary {
    margin: 0 0 1rem;
    line-height: 1.5;

    :deep(p) { margin: 0 0 0.3rem; }
    :deep(ul) { margin: 0 0 0.3rem; padding-left: 1.2em; }
    :deep(li) { margin: 0.1rem 0; }
    :deep(strong) { font-weight: 600; }
  }

  &__h4 {
    margin: 0 0 0.4rem;
    font-size: 13px;
  }

  &__note {
    margin: 0 0 1rem;
    line-height: 1.5;

    :deep(p) { margin: 0 0 0.3rem; }
    :deep(strong) { font-weight: 600; }
    :deep(code) { font-family: $mono; font-size: 0.85em; }
  }

  &__matrix {
    border-top: 1px solid $border;
    padding-top: 0.75rem;
  }
}

.matrix {
  &__row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding: 0.35rem 0;
    border-bottom: 1px solid $border;
  }

  &__id {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    font-size: 12px;
  }
}

.attacks {
  overflow: auto;
  padding: 1rem;

  &__intro {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 1rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid $border;
  }

  &__eyebrow {
    display: block;
    color: $text-dim;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.15rem;
  }

  &__group {
    margin-bottom: 1.25rem;
  }

  &__label {
    margin: 0 0 0.5rem;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: $text-dim;
  }

  &__empty {
    text-align: center;
    margin-top: 2rem;
  }
}

.probe {
  @include card;
  margin-bottom: 0.6rem;

  &__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
  }

  &__title {
    font-weight: 600;
  }

  &__prompt {
    margin: 0.4rem 0 0.3rem;
    font-style: italic;
  }

  &__why {
    margin: 0 0 0.6rem;
    font-size: 12px;
    line-height: 1.45;
  }

  &__load {
    background: $accent;
    color: $bg;
    font-weight: 600;
  }
}
</style>
