<script setup lang="ts">
import { toRef } from "vue";

import SanitizedHtml from "@/components/SanitizedHtml";
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
    <SanitizedHtml
      v-else
      class="mermaid__host"
      :html="svg"
      :svg="true"
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
