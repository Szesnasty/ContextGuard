<script setup lang="ts">
import IdentityPicker from "@/components/IdentityPicker.vue";
import RagDrawer from "@/components/RagDrawer.vue";
import { useQueryConsole } from "@/composables/useQueryConsole";
import { tally, tokenReduction } from "@/lib/firewall";

const {
  input,
  k,
  messages,
  error,
  isSending,
  drawerOpen,
  drawerRun,
  emptyGuard,
  send,
  openDrawer,
  closeDrawer,
} = useQueryConsole();
</script>

<template>
  <section class="console">
    <header class="console__head">
      <h1 class="console__title">
        RAG Console
      </h1>
      <p class="muted">
        Ask a question. The model answers from retrieved documents — then the firewall shows you
        which sources it would <em>allow</em>, <em>redact</em> or <em>block</em> for your identity.
      </p>
    </header>

    <IdentityPicker />

    <div class="console__thread">
      <p
        v-if="!messages.length"
        class="console__empty muted"
      >
        No messages yet. Try “What is our refund policy?” or “Show me the API keys”.
      </p>

      <article
        v-for="message in messages"
        :key="message.id"
        class="bubble"
        :class="`bubble--${message.role}`"
      >
        <div class="bubble__role">
          {{ message.role }}
        </div>
        <p class="bubble__text">
          {{ message.text }}
        </p>

        <div
          v-if="message.run"
          class="bubble__evidence"
        >
          <span class="tag tag--allowed">{{ tally(message.run.guarded).allowed }} allowed</span>
          <span class="tag tag--redacted">{{ tally(message.run.guarded).redacted }} redacted</span>
          <span class="tag tag--blocked">{{ tally(message.run.guarded).blocked }} blocked</span>
          <span class="muted">−{{ tokenReduction(message.run.guarded) }}% tokens</span>
          <button
            class="ghost bubble__open"
            @click="openDrawer(message.run)"
          >
            View {{ message.run.retrieved.length }} sources →
          </button>
        </div>
      </article>
    </div>

    <div
      v-if="error"
      class="banner banner--err console__error"
    >
      {{ error }}
    </div>

    <form
      class="composer"
      @submit.prevent="send"
    >
      <textarea
        v-model="input"
        class="composer__input"
        rows="2"
        placeholder="Ask the documents…"
        @keydown.enter.exact.prevent="send"
      />
      <div class="composer__controls">
        <label class="composer__k">
          k
          <input
            v-model.number="k"
            type="number"
            min="1"
            max="50"
          >
        </label>
        <button
          type="submit"
          :disabled="isSending"
        >
          {{ isSending ? "Running…" : "Send" }}
        </button>
      </div>
    </form>

    <RagDrawer
      :open="drawerOpen"
      :query="drawerRun?.query ?? ''"
      :retrieved="drawerRun?.retrieved ?? []"
      :guarded="drawerRun?.guarded ?? emptyGuard"
      @close="closeDrawer"
    />
  </section>
</template>

<style scoped lang="scss">
@use "@/styles/tokens" as *;

.console {
  display: flex;
  flex-direction: column;
  gap: $gap;
  max-width: 920px;
  margin: 0 auto;

  &__head {
    margin-bottom: 0.25rem;
  }

  &__title {
    margin: 0 0 0.25rem;
  }

  &__thread {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    min-height: 120px;
  }

  &__empty {
    padding: 1.5rem 0;
    text-align: center;
  }

  &__error {
    margin: 0;
  }
}

.bubble {
  @include card;
  max-width: 86%;

  &--user {
    align-self: flex-end;
    background: $bg-elev-2;
  }

  &--assistant {
    align-self: flex-start;
  }

  &__role {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: $text-dim;
    margin-bottom: 0.3rem;
  }

  &__text {
    margin: 0;
    white-space: pre-wrap;
  }

  &__evidence {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    flex-wrap: wrap;
    margin-top: 0.6rem;
    padding-top: 0.6rem;
    border-top: 1px solid $border;
  }

  &__open {
    margin-left: auto;
  }
}

.composer {
  @include card;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  position: sticky;
  bottom: 0;

  &__input {
    resize: vertical;
  }

  &__controls {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    justify-content: flex-end;
  }

  &__k {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    color: $text-dim;
    font-size: 13px;

    input {
      width: 64px;
    }
  }
}
</style>
