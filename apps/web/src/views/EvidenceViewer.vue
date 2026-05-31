<script setup lang="ts">
import "diff2html/bundles/css/diff2html.min.css";

import DecisionsTable from "@/components/DecisionsTable.vue";
import MermaidDiagram from "@/components/MermaidDiagram.vue";
import { useEvidenceViewer } from "@/composables/useEvidenceViewer";

const {
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
} = useEvidenceViewer();
</script>

<template>
  <section class="evidence">
    <header class="evidence__head">
      <h1 class="evidence__title">
        Evidence Viewer
      </h1>
      <p class="muted">
        Re-open any console run to see <em>what</em> the firewall did and <em>why</em>: the decision
        flow, the context diff sent to the model, and every enforced policy.
      </p>
    </header>

    <p
      v-if="!hasRuns"
      class="card muted"
    >
      No runs yet. Ask something in the <RouterLink to="/console">
        Console
      </RouterLink> first.
    </p>

    <div
      v-else
      class="evidence__layout"
    >
      <nav class="runs card">
        <button
          v-for="run in runs"
          :key="run.id"
          class="runs__item"
          :class="{ 'runs__item--active': run.id === selected?.id }"
          @click="selectRun(run.id)"
        >
          <div class="runs__query">
            {{ run.query }}
          </div>
          <div class="runs__meta muted">
            {{ run.identity }}
          </div>
        </button>
      </nav>

      <div
        v-if="selected"
        class="detail"
      >
        <div
          class="banner"
          :class="contained ? 'banner--ok' : 'banner--leak'"
        >
          {{ contained ? "✓ Firewall withheld at least one source from the prompt." : "⚠️ Nothing was withheld — every retrieved source reached the model." }}
        </div>

        <div
          v-if="counts"
          class="detail__stats"
        >
          <div class="stat">
            <span class="stat__n">{{ counts.allowed }}</span><span class="stat__k">allowed</span>
          </div>
          <div class="stat">
            <span class="stat__n">{{ counts.redacted }}</span><span class="stat__k">redacted</span>
          </div>
          <div class="stat">
            <span class="stat__n">{{ counts.blocked }}</span><span class="stat__k">blocked</span>
          </div>
          <div class="stat">
            <span class="stat__n">−{{ reduction }}%</span><span class="stat__k">tokens</span>
          </div>
        </div>

        <div class="card">
          <h2 class="detail__h">
            Decision flow
          </h2>
          <MermaidDiagram :definition="flow" />
        </div>

        <div class="card">
          <h2 class="detail__h">
            Context diff — retrieved vs. sent to model
          </h2>
          <!-- eslint-disable-next-line vue/no-v-html -->
          <div
            class="detail__diff"
            v-html="contextDiff"
          />
        </div>

        <div class="card">
          <h2 class="detail__h">
            Enforced decisions
          </h2>
          <DecisionsTable :decisions="enforcedDecisions" />
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped lang="scss">
@use "@/styles/tokens" as *;

.evidence {
  display: flex;
  flex-direction: column;
  gap: $gap;

  &__title {
    margin: 0 0 0.25rem;
  }

  &__layout {
    display: grid;
    grid-template-columns: 260px minmax(0, 1fr);
    gap: $gap;
    align-items: start;
  }
}

.runs {
  padding: 0;
  overflow: hidden;

  &__item {
    width: 100%;
    text-align: left;
    background: transparent;
    color: $text;
    border: none;
    border-bottom: 1px solid $border;
    border-radius: 0;
    padding: 0.6rem 0.75rem;
    cursor: pointer;

    &:hover {
      background: $bg-elev-2;
    }

    &--active {
      background: $bg-elev-2;
      box-shadow: inset 3px 0 0 $accent;
    }
  }

  &__query {
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__meta {
    font-size: 12px;
  }
}

.detail {
  display: flex;
  flex-direction: column;
  gap: $gap;
  min-width: 0;

  &__stats {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  &__h {
    margin: 0 0 0.75rem;
    font-size: 15px;
  }

  &__diff {
    overflow-x: auto;
    max-width: 100%;
  }
}
</style>
