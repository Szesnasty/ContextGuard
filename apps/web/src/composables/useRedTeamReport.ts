// Red Team logic: load the generated RED-TEAM.md report (copied into /public by
// the prebuild step) and render it to HTML with marked. The SFC just shows the
// loading/error state and the rendered report.
import { marked } from "marked";
import { onMounted, ref } from "vue";

import { sanitizeHtml } from "@/lib/firewall";

export function useRedTeamReport() {
  const html = ref("");
  const error = ref<string | null>(null);
  const isLoading = ref(true);

  async function load() {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await fetch("/reports/RED-TEAM.md");
      if (!response.ok) {
        throw new Error(`Report unavailable (HTTP ${response.status}). Run \`make red-team\`.`);
      }
      const markdown = await response.text();
      html.value = sanitizeHtml(await marked.parse(markdown));
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : String(cause);
    } finally {
      isLoading.value = false;
    }
  }

  onMounted(load);

  return { html, error, isLoading, reload: load };
}
