import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/console" },
    {
      path: "/console",
      name: "console",
      component: () => import("@/views/QueryConsole.vue"),
      meta: { title: "Query Console" },
    },
    {
      path: "/evidence",
      name: "evidence",
      component: () => import("@/views/EvidenceViewer.vue"),
      meta: { title: "Evidence Viewer" },
    },
    {
      path: "/policy",
      name: "policy",
      component: () => import("@/views/PolicyEditor.vue"),
      meta: { title: "Policy Editor" },
    },
    {
      path: "/red-team",
      name: "red-team",
      component: () => import("@/views/RedTeamRuns.vue"),
      meta: { title: "Red Team Runs" },
    },
  ],
});

export default router;
