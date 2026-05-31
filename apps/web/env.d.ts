/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Absolute API origin. Empty -> same-origin (dev uses the Vite proxy). */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<Record<string, never>, Record<string, never>, unknown>;
  export default component;
}
