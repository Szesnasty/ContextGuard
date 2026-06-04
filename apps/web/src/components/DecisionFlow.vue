<script setup lang="ts">
import { computed } from "vue";

import type { GuardedContext } from "@/api/types";
import { tally } from "@/lib/firewall";

const props = defineProps<{
  retrieved: number;
  guarded: GuardedContext;
}>();

const counts = computed(() => tally(props.guarded));
const promptTokens = computed(() => props.guarded.tokens_after ?? 0);
</script>

<template>
  <div
    class="decision-flow"
    aria-label="ContextGuard decision flow"
  >
    <div class="flow-card flow-card--source">
      <span class="flow-card__k">Retrieved</span>
      <strong class="flow-card__n">{{ retrieved }}</strong>
      <span class="flow-card__d">candidate chunks</span>
    </div>

    <div class="flow-rule" />

    <div class="flow-card flow-card--gate">
      <span class="flow-card__k">Policy gate</span>
      <strong class="flow-card__n">tenant role purpose</strong>
      <span class="flow-card__d">classification and risk signals</span>
    </div>

    <div class="flow-rule" />

    <div class="flow-stack">
      <div class="flow-card flow-card--allowed">
        <span class="flow-card__k">Allowed</span>
        <strong class="flow-card__n">{{ counts.allowed }}</strong>
        <span class="flow-card__d">sent to prompt</span>
      </div>
      <div class="flow-card flow-card--redacted">
        <span class="flow-card__k">Redacted</span>
        <strong class="flow-card__n">{{ counts.redacted }}</strong>
        <span class="flow-card__d">masked then sent</span>
      </div>
      <div class="flow-card flow-card--blocked">
        <span class="flow-card__k">Blocked</span>
        <strong class="flow-card__n">{{ counts.blocked }}</strong>
        <span class="flow-card__d">withheld from model</span>
      </div>
    </div>

    <div class="flow-rule" />

    <div class="flow-card flow-card--prompt">
      <span class="flow-card__k">Prompt</span>
      <strong class="flow-card__n">{{ promptTokens }}</strong>
      <span class="flow-card__d">tokens after firewall</span>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use "@/styles/tokens" as *;

.decision-flow {
  display: grid;
  grid-template-columns: minmax(120px, 0.9fr) 36px minmax(150px, 1fr) 36px minmax(180px, 1.2fr) 36px minmax(120px, 0.9fr);
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  overflow-x: auto;
  border: 1px solid $border;
  border-radius: $radius;
  background: $bg;
}

.flow-rule {
  height: 2px;
  min-width: 32px;
  background: linear-gradient(90deg, $border, $accent);
}

.flow-stack {
  display: grid;
  gap: 0.5rem;
}

.flow-card {
  display: grid;
  gap: 0.15rem;
  min-height: 84px;
  padding: 0.75rem;
  border: 1px solid $border;
  border-radius: $radius;
  background: $bg-elev-2;

  &__k {
    color: $text-dim;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  &__n {
    color: $text;
    font-size: 22px;
    line-height: 1.1;
  }

  &__d {
    color: $text-dim;
    font-size: 12px;
  }

  &--allowed {
    border-color: rgba($allowed, 0.7);
    background: rgba($allowed, 0.12);
  }

  &--redacted {
    border-color: rgba($redacted, 0.7);
    background: rgba($redacted, 0.12);
  }

  &--blocked {
    border-color: rgba($blocked, 0.7);
    background: rgba($blocked, 0.12);
  }

  &--prompt {
    border-color: rgba($accent, 0.7);
    background: rgba($accent, 0.12);
  }
}

@media (max-width: 900px) {
  .decision-flow {
    grid-template-columns: minmax(180px, 1fr);
  }

  .flow-rule {
    width: 2px;
    height: 24px;
    justify-self: center;
    min-width: 0;
    background: linear-gradient(180deg, $border, $accent);
  }
}
</style>
