<script setup lang="ts">
import { useModelPicker } from "@/composables/useModelPicker";

const {
  chatModels,
  activeModel,
  presets,
  isLoading,
  isSwitching,
  isPulling,
  installingModel,
  error,
  hasNoModels,
  ollamaUnavailable,
  ollamaDownloadUrl,
  formatSize,
  selectModel,
  isInstalled,
  isActive,
  presetAction,
  usePreset,
} = useModelPicker();
</script>

<template>
  <div class="card model">
    <div
      v-if="ollamaUnavailable"
      class="model__setup"
    >
      <div>
        <strong>Ollama is not running</strong>
        <p class="muted">
          Install Ollama, start it, then use the one-click model buttons here.
        </p>
      </div>
      <a
        class="model__setup-link"
        :href="ollamaDownloadUrl"
        target="_blank"
        rel="noreferrer"
      >
        Download Ollama
      </a>
    </div>

    <div
      v-else-if="hasNoModels"
      class="model__setup"
    >
      <div>
        <strong>No local chat model installed</strong>
        <p class="muted">
          Choose one of the presets. ContextGuard will download it and switch to it.
        </p>
      </div>
    </div>

    <div class="model__row">
      <div class="model__field">
        <label for="chat-model">Chat model</label>
        <select
          id="chat-model"
          :value="activeModel"
          :disabled="isLoading || isSwitching || !chatModels.length"
          @change="selectModel(($event.target as HTMLSelectElement).value)"
        >
          <option
            v-if="!chatModels.length"
            value=""
          >
            {{ isLoading ? "Loading…" : "No chat models installed" }}
          </option>
          <option
            v-for="model in chatModels"
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

      <div class="model__field model__field--presets">
        <span class="model__label">One-click models</span>
        <div class="model__presets">
          <button
            v-for="preset in presets"
            :key="preset.name"
            class="model__preset"
            :class="{ 'model__preset--active': isActive(preset.name) }"
            :disabled="ollamaUnavailable || isLoading || isSwitching || isPulling || isActive(preset.name)"
            @click="usePreset(preset.name)"
          >
            <span class="model__preset-main">
              <span class="model__preset-label">{{ preset.label }}</span>
              <span class="model__preset-name">{{ preset.name }}</span>
            </span>
            <span class="model__preset-meta">
              {{ isInstalled(preset.name) ? "Installed" : preset.description }}
            </span>
            <span class="model__preset-action">
              {{
                installingModel === preset.name
                  ? "Installing..."
                  : presetAction(preset.name)
              }}
            </span>
          </button>
        </div>
        <span class="muted model__hint">
          Pick a preset. Missing models download from Ollama, then become active automatically.
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

  &__setup {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding-bottom: 0.75rem;
    margin-bottom: 0.75rem;
    border-bottom: 1px solid $border;

    p {
      margin: 0.25rem 0 0;
    }
  }

  &__setup-link {
    border: 1px solid $accent;
    border-radius: $radius;
    color: $accent;
    font-weight: 700;
    padding: 0.5rem 0.75rem;
    text-decoration: none;
    white-space: nowrap;

    &:hover {
      background: rgba($accent, 0.12);
    }
  }

  &__field {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    flex: 1;
    min-width: 240px;

    &--presets {
      flex: 1.45;
    }
  }

  &__label {
    color: $text-dim;
    font-size: 12px;
  }

  &__presets {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.5rem;
  }

  &__preset {
    min-height: 88px;
    text-align: left;
    background: $bg;
    color: $text;
    border: 1px solid $border;
    border-radius: $radius;
    padding: 0.65rem;
    display: grid;
    gap: 0.35rem;
    align-content: space-between;

    &:hover:not(:disabled) {
      border-color: $accent;
      background: rgba($accent, 0.08);
    }

    &--active {
      border-color: rgba($allowed, 0.65);
      background: rgba($allowed, 0.1);
    }
  }

  &__preset-main {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  &__preset-label {
    font-weight: 700;
  }

  &__preset-name,
  &__preset-meta {
    color: $text-dim;
    font-size: 12px;
  }

  &__preset-name {
    font-family: $mono;
    white-space: nowrap;
  }

  &__preset-action {
    color: $accent;
    font-weight: 700;
    font-size: 12px;
  }

  &__hint {
    font-size: 12px;
  }

  &__warn {
    margin-top: 0.6rem;
  }
}

@media (max-width: 760px) {
  .model {
    &__setup {
      align-items: flex-start;
      flex-direction: column;
    }

    &__presets {
      grid-template-columns: 1fr;
    }
  }
}
</style>
