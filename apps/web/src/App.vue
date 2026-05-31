<script setup lang="ts">
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
</script>

<template>
  <div class="shell">
    <header class="shell__bar">
      <div class="shell__brand">
        ContextGuard <small>firewall dashboard</small>
      </div>
      <nav class="shell__nav">
        <RouterLink to="/console">
          Console
        </RouterLink>
        <RouterLink to="/evidence">
          Evidence
        </RouterLink>
        <RouterLink to="/policy">
          Policy
        </RouterLink>
      </nav>
      <span
        class="shell__identity"
        :class="{ 'shell__identity--unset': !auth.isAuthenticated }"
      >
        {{ auth.label }}
      </span>
    </header>

    <main class="shell__main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped lang="scss">
@use "@/styles/tokens" as *;

.shell {
  display: grid;
  grid-template-rows: auto 1fr;
  height: 100%;

  &__bar {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    padding: 0.75rem 1.25rem;
    background: $bg-elev;
    border-bottom: 1px solid $border;
  }

  &__brand {
    font-weight: 700;
    letter-spacing: 0.02em;

    small {
      color: $text-dim;
      font-weight: 400;
      margin-left: 0.4rem;
    }
  }

  &__nav {
    display: flex;
    gap: 0.25rem;

    a {
      padding: 0.4rem 0.75rem;
      border-radius: 6px;
      color: $text-dim;

      &.router-link-active {
        background: $bg-elev-2;
        color: $text;
      }
    }
  }

  &__identity {
    margin-left: auto;
    font-family: $mono;
    font-size: 12px;
    color: $text-dim;

    &--unset {
      opacity: 0.7;
    }
  }

  &__main {
    overflow: auto;
    padding: 1.25rem;
  }
}
</style>

