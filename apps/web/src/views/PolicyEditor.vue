<script setup lang="ts">
import { ref } from "vue";

import { useMonacoPolicy } from "@/composables/useMonacoPolicy";

const host = ref<HTMLElement | null>(null);
const { errors, parseError, isValid, ruleCount, download } = useMonacoPolicy(host);
</script>

<template>
  <section class="policy">
    <header class="policy__head">
      <div>
        <h1 class="policy__title">
          Policy Editor
        </h1>
        <p class="muted">
          Edit the firewall policy DSL. It validates live against the contracts'
          <code>policy.schema.json</code> — the same schema the API enforces.
        </p>
      </div>
      <button
        class="ghost"
        @click="download"
      >
        Download YAML
      </button>
    </header>

    <div class="policy__status">
      <span
        v-if="parseError"
        class="tag tag--blocked"
      >YAML error</span>
      <span
        v-else-if="isValid"
        class="tag tag--allowed"
      >valid · {{ ruleCount }} rule(s)</span>
      <span
        v-else
        class="tag tag--redacted"
      >{{ errors.length }} schema issue(s)</span>
    </div>

    <div
      ref="host"
      class="policy__editor"
    />

    <div
      v-if="parseError"
      class="banner banner--err policy__errors"
    >
      {{ parseError }}
    </div>
    <ul
      v-else-if="errors.length"
      class="policy__errors card"
    >
      <li
        v-for="(error, index) in errors"
        :key="index"
      >
        <code>{{ error.path }}</code> — {{ error.message }}
      </li>
    </ul>
  </section>
</template>

<style scoped lang="scss">
@use "@/styles/tokens" as *;

.policy {
  display: flex;
  flex-direction: column;
  gap: $gap;

  &__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
  }

  &__title {
    margin: 0 0 0.25rem;
  }

  &__editor {
    height: 60vh;
    min-height: 360px;
    border: 1px solid $border;
    border-radius: $radius;
    overflow: hidden;
  }

  &__errors {
    margin: 0;

    li {
      margin: 0.2rem 0;
    }
  }
}
</style>
