<script setup lang="ts">
import { toRef } from "vue";

import { useMermaid } from "@/composables/useMermaid";

const props = defineProps<{ definition: string }>();
const { svg, error } = useMermaid(toRef(props, "definition"));
</script>

<template>
  <div class="mermaid">
    <div
      v-if="error"
      class="banner banner--err"
    >
      {{ error }}
    </div>
    <!-- eslint-disable-next-line vue/no-v-html -->
    <div
      v-else
      class="mermaid__host"
      v-html="svg"
    />
  </div>
</template>

<style scoped lang="scss">
@use "@/styles/tokens" as *;

.mermaid {
  &__host {
    background: white;
    border-radius: $radius;
    padding: 1rem;
    overflow: auto;
  }
}
</style>

