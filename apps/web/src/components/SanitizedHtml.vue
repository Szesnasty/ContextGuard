<script setup lang="ts">
import { computed } from "vue";

import { sanitizeHtml } from "@/lib/sanitize";

const props = withDefaults(defineProps<{
  html: string;
  svg?: boolean;
  tag?: string;
}>(), {
  svg: false,
  tag: "div",
});

const cleanHtml = computed(() => sanitizeHtml(props.html, { svg: props.svg }));
</script>

<template>
  <article
    v-if="tag === 'article'"
    v-html="cleanHtml"
  />
  <span
    v-else-if="tag === 'span'"
    v-html="cleanHtml"
  />
  <div
    v-else
    v-html="cleanHtml"
  />
</template>
