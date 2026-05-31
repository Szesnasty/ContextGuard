// Evidence Viewer logic: reads past runs from the history store and, for the
// selected run, derives the firewall's evidence — a flow diagram, the
// before/after context delta, and the enforced (blocked/redacted) decisions.
import { diffLines } from "diff";
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

/** One rendered line of the context delta: kept context, or withheld/added. */
export interface DeltaLine {
  id: number;
  type: "context" | "removed" | "added";
  text: string;
}


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

  const contextDelta = computed<DeltaLine[]>(() => {
    if (!selected.value) return [];
    const before = contextBefore(selected.value.retrieved);
    const after = contextAfter(selected.value.guarded);
    const lines: DeltaLine[] = [];
    let id = 0;
    for (const part of diffLines(before, after)) {
      const type = part.added ? "added" : part.removed ? "removed" : "context";
      for (const raw of part.value.split("\n")) {
        if (!raw.length) continue;
        lines.push({ id: id++, type, text: raw });
      }
    }
    return lines;
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
    contextDelta,
    selectRun,
  };
}
