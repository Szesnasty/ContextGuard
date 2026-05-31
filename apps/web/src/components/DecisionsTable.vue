<script setup lang="ts">
import { FlexRender } from "@tanstack/vue-table";
import { toRef } from "vue";

import type { ChunkDecision, Outcome } from "@/api/types";
import { useDecisionsTable } from "@/composables/useDecisionsTable";
import { outcomeClass } from "@/lib/firewall";

const props = defineProps<{ decisions: ChunkDecision[] }>();
const { table, isEmpty } = useDecisionsTable(toRef(props, "decisions"));
</script>

<template>
  <table>
    <thead>
      <tr
        v-for="headerGroup in table.getHeaderGroups()"
        :key="headerGroup.id"
      >
        <th
          v-for="header in headerGroup.headers"
          :key="header.id"
        >
          <FlexRender
            v-if="!header.isPlaceholder"
            :render="header.column.columnDef.header"
            :props="header.getContext()"
          />
        </th>
      </tr>
    </thead>
    <tbody>
      <tr v-if="isEmpty">
        <td
          colspan="4"
          class="muted"
        >
          No blocked or redacted chunks — nothing to show.
        </td>
      </tr>
      <tr
        v-for="row in table.getRowModel().rows"
        :key="row.id"
      >
        <template
          v-for="cell in row.getVisibleCells()"
          :key="cell.id"
        >
          <td v-if="cell.column.id === 'chunk_id'">
            <code>{{ cell.getValue() }}</code>
          </td>
          <td v-else-if="cell.column.id === 'outcome'">
            <span :class="outcomeClass(cell.getValue() as Outcome)">{{ cell.getValue() }}</span>
          </td>
          <td v-else>
            <FlexRender
              :render="cell.column.columnDef.cell"
              :props="cell.getContext()"
            />
          </td>
        </template>
      </tr>
    </tbody>
  </table>
</template>

