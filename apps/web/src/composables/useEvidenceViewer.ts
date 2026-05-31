// Evidence Viewer logic: reads past runs from the history store and, for the
// selected run, derives the firewall's evidence — a flow diagram, the
// before/after context diff, and the enforced (blocked/redacted) decisions.
import { createTwoFilesPatch } from "diff";
import { html as diffHtml } from "diff2html";
import { computed } from "vue";

import {
  contextAfter,
  contextBefore,
  enforced,
  evidenceFlow,
  isContained,
  tally,
  tokenReduction,
} from "@/lib/firewall";
import { useHistoryStore } from "@/stores/history";

export function useEvidenceViewer() {
  const history = useHistoryStore();

  const runs = computed(() => history.runs);
  const selected = computed(() => history.selected);
  const hasRuns = computed(() => runs.value.length > 0);

  const flow = computed(() => {
    if (!selected.value) return "";
    return evidenceFlow(selected.value.retrieved.length, selected.value.guarded);
  });

  const counts = computed(() => (selected.value ? tally(selected.value.guarded) : null));
  const reduction = computed(() =>
    selected.value ? tokenReduction(selected.value.guarded) : 0,
  );
  const contained = computed(() =>
    selected.value ? isContained(selected.value.guarded) : false,
  );
  const enforcedDecisions = computed(() =>
    selected.value ? enforced(selected.value.guarded) : [],
  );

  const contextDiff = computed(() => {
    if (!selected.value) return "";
    const before = contextBefore(selected.value.retrieved);
    const after = contextAfter(selected.value.guarded);
    const patch = createTwoFilesPatch(
      "retrieved-context",
      "guarded-context",
      `${before}\n`,
      `${after}\n`,
    );
    return diffHtml(patch, {
      drawFileList: false,
      matching: "lines",
      outputFormat: "side-by-side",
    });
  });

  function selectRun(id: string) {
    history.select(id);
  }

  return {
    runs,
    selected,
    hasRuns,
    flow,
    counts,
    reduction,
    contained,
    enforcedDecisions,
    contextDiff,
    selectRun,
  };
}
