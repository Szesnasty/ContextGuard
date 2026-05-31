// Copy the committed firewall reports into the web app's public/ dir so the
// "Red Team Runs" view can fetch them as static assets. Run via `pnpm copy:reports`
// (wired into prebuild). Idempotent; safe to run repeatedly.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "..", "..", "..");
const outDir = resolve(here, "..", "public", "reports");

const REPORTS = ["RED-TEAM.md", "BENCHMARK.md"];

mkdirSync(outDir, { recursive: true });

for (const name of REPORTS) {
  const src = resolve(repoRoot, name);
  if (!existsSync(src)) {
    console.warn(`copy-reports: ${name} not found at repo root, skipping`);
    continue;
  }
  copyFileSync(src, resolve(outDir, name));
  console.log(`copy-reports: ${name} -> public/reports/${name}`);
}
