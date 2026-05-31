<script setup lang="ts">
import { useIdentityPicker } from "@/composables/useIdentityPicker";

const {
  auth,
  tokenDraft,
  isMinting,
  mintError,
  identities,
  activeIdentity,
  mintHint,
  canSaveToken,
  selectIdentity,
  saveToken,
  removeToken,
  generateToken,
} = useIdentityPicker();
</script>

<template>
  <div class="card picker">
    <div class="picker__row">
      <div class="picker__field picker__field--narrow">
        <label for="identity">Identity (tenant · role)</label>
        <select
          id="identity"
          :value="auth.activeSub"
          @change="selectIdentity(($event.target as HTMLSelectElement).value)"
        >
          <option
            v-for="identity in identities"
            :key="identity.sub"
            :value="identity.sub"
          >
            {{ identity.sub }} — {{ identity.role }} @ {{ identity.tenant }}
          </option>
        </select>
      </div>

      <div class="picker__field">
        <label>Active token</label>
        <div
          v-if="auth.isAuthenticated"
          class="picker__status"
        >
          <span class="tag tag--allowed">token set</span>
          <span class="picker__identity">{{ auth.label }}</span>
          <button
            class="ghost"
            @click="removeToken"
          >
            Remove
          </button>
        </div>
        <span
          v-else
          class="muted"
        >No token for this identity yet.</span>
      </div>
    </div>

    <div
      v-if="auth.slotMismatch"
      class="banner banner--leak picker__warn"
    >
      ⚠️ This token decodes as <code>{{ auth.identity?.sub }}</code>, not the selected
      <code>{{ auth.activeSub }}</code>. The API trusts the token, not the picker.
    </div>

    <div
      v-if="!auth.isAuthenticated"
      class="picker__mint"
    >
      <button
        class="picker__generate"
        :disabled="isMinting"
        @click="generateToken"
      >
        {{ isMinting ? "Generating…" : `Generate token for ${activeIdentity?.sub}` }}
      </button>
      <span class="muted picker__hint">Dev-only — disabled in production.</span>

      <p
        v-if="mintError"
        class="banner banner--err picker__warn"
      >
        {{ mintError }}
      </p>

      <details class="picker__manual">
        <summary>Paste a token instead</summary>
        <label>Mint with the CLI, then paste it:</label>
        <pre class="picker__cmd">{{ mintHint }}</pre>
        <textarea
          v-model="tokenDraft"
          rows="2"
          placeholder="eyJhbGciOi..."
        />
        <button
          class="picker__save"
          :disabled="!canSaveToken"
          @click="saveToken"
        >
          Save token
        </button>
      </details>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use "@/styles/tokens" as *;

.picker {
  &__row {
    display: flex;
    gap: $gap;
    align-items: flex-end;
    flex-wrap: wrap;
  }

  &__field {
    flex: 1;
    min-width: 240px;

    &--narrow {
      flex: 0 0 220px;
    }
  }

  &__status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  &__identity {
    font-family: $mono;
    font-size: 12px;
    color: $text-dim;
  }

  &__warn {
    margin-top: 0.6rem;
  }

  &__mint {
    margin-top: 0.6rem;
  }

  &__generate {
    background: $accent;
    color: $bg;
    font-weight: 600;
  }

  &__hint {
    margin-left: 0.5rem;
    font-size: 12px;
  }

  &__manual {
    margin-top: 0.6rem;

    summary {
      cursor: pointer;
      color: $text-dim;
      font-size: 13px;
    }
  }

  &__cmd {
    margin: 0.25rem 0;
    color: $text-dim;
  }

  &__save {
    margin-top: 0.4rem;
  }
}
</style>

