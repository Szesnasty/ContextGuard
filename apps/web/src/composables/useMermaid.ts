// Renders a Mermaid definition to SVG, re-rendering when it changes. All Mermaid
// interaction is isolated here so the component stays presentational.
import mermaid from "mermaid";
import { ref, watch, type Ref } from "vue";

import { sanitizeHtml } from "@/lib/firewall";

mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "strict" });

export function useMermaid(definition: Ref<string>) {
  const svg = ref("");
  const error = ref<string | null>(null);
  let renderSeq = 0;

  async function render(source: string) {
    error.value = null;

    if (!source.trim()) {
      svg.value = "";
      return;
    }

    try {
      const result = await mermaid.render(`mermaid-${renderSeq++}`, source);
      svg.value = sanitizeHtml(result.svg, { svg: true });
    } catch (cause) {
      error.value = (cause as Error).message ?? "Failed to render diagram.";
      svg.value = "";
    }
  }

  watch(definition, render, { immediate: true });

  return { svg, error };
}
