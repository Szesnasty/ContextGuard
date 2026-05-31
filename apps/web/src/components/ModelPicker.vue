<script setup lang="ts">
import { useModelPicker } from "@/composables/useModelPicker";

const {
  models,
  activeModel,
  pullName,
  isLoading,
  isSwitching,
  isPulling,
  error,
  canPull,
  formatSize,
  selectModel,
  pull,
} = useModelPicker();
</script>

<template>
  <div class="card model">
    <div class="model__row">
      <div class="model__field">
        <label for="chat-model">Chat model</label>
        <select
          id="chat-model"
          :value="activeModel"
          :disabled="isLoading || isSwitching || !models.length"
          @change="selectModel(($event.target as HTMLSelectElement).value)"
        >
          <option
            v-if="!models.length"
            value=""
          >
            {{ isLoading ? "Loading…" : "No models installed" }}
          </option>
          <option
            v-for="model in models"
            :key="model.name"
            :value="model.name"
          >
            {{ model.name }}{{ formatSize(model.size_bytes) ? ` · ${formatSize(model.size_bytes)}` : "" }}
          </option>
        </select>
        <span class="muted model__hint">
          {{ isSwitching ? "Switching…" : "Used by the live query path. Dev-only — disabled in production." }}
        </span>
      </div>

      <div class="model__field model__field--pull">
        <label for="pull-model">Install a model</label>
        <div class="model__pull">
          <input
            id="pull-model"
            v-model="pullName"
            placeholder="e.g. qwen2.5:7b"
            @keyup.enter="pull"
          >
          <button
            class="model__btn"
            :disabled="!canPull"
            @click="pull"
          >
            {{ isPulling ? "Pulling…" : "Pull" }}
          </button>
        </div>
        <span class="muted model__hint">
          Downloads from the Ollama library. Larger models take a while.
        </span>
      </div>
    </div>

    <p
      v-if="error"
      class="banner banner--err model__warn"
    >
      {{ error }}
    </p>
  </div>
</template>

<style scoped lang="scss">
@use "@/styles/tokens" as *;

.model {
  &__row {
    display: flex;
    gap: $gap;
    align-items: flex-start;
    flex-wrap: wrap;
  }

  &__field {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    flex: 1;
    min-width: 240px;

    &--pull {
      flex: 1.2;
    }
  }

  &__pull {
    display: flex;
    gap: 0.5rem;

    input {
      flex: 1;
      min-width: 0;
    }
  }

  &__btn {
    background: $accent;
    color: $bg;
    font-weight: 600;
    white-space: nowrap;
  }

  &__hint {
    font-size: 12px;
  }

  &__warn {
    margin-top: 0.6rem;
  }
}
</style>
