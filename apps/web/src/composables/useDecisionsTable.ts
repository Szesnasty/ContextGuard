// Builds the TanStack table model for the firewall decisions table. Column defs
// and the table instance live here, keeping the component to pure rendering.
import {
  getCoreRowModel,
  useVueTable,
  type ColumnDef,
} from "@tanstack/vue-table";
import { computed, type Ref } from "vue";

import type { ChunkDecision } from "@/api/types";

export function useDecisionsTable(decisions: Ref<ChunkDecision[]>) {
  const columns: ColumnDef<ChunkDecision>[] = [
    { accessorKey: "chunk_id", header: "Chunk" },
    { accessorKey: "outcome", header: "Outcome" },
    {
      accessorKey: "policies_triggered",
      header: "Policies",
      cell: (ctx) => (ctx.getValue() as string[]).join(", ") || "—",
    },
    {
      accessorKey: "reasons",
      header: "Reasons",
      cell: (ctx) => (ctx.getValue() as string[]).join("; ") || "—",
    },
  ];

  const isEmpty = computed(() => decisions.value.length === 0);

  const table = useVueTable({
    get data() {
      return decisions.value;
    },
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return { table, isEmpty };
}
