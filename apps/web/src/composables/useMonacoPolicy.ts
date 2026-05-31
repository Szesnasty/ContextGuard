// Policy Editor logic: a Monaco YAML editor over the ContextGuard policy DSL,
// validated live against the contracts' policy JSON-schema (the single source of
// truth — ADR-004). Parsing + validation are pure-ish; the SFC only hosts the
// editor element and renders the error list.
import Ajv, { type ErrorObject } from "ajv";
import addFormats from "ajv-formats";
import * as monaco from "monaco-editor";
import editorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";
import { onBeforeUnmount, onMounted, ref, type Ref } from "vue";
import { parse } from "yaml";

import policySchema from "../../../../packages/contracts/schemas/policy.schema.json";

// Monaco needs its editor web-worker; we use only the base worker (no language
// servers), which is enough for YAML tokenizing + the editing experience.
self.MonacoEnvironment = {
  getWorker: () => new editorWorker(),
};

const DEFAULT_POLICY = `version: 1
default_effect: allow

roles:
  manager:
    inherits: [sales]

rules:
  - id: tenant-isolation
    description: A user may never see another tenant's chunks.
    effect: deny
    priority: 100
    when:
      - { field: chunk.tenant, op: neq, ref: user.tenant }

  - id: sales-no-confidential
    description: The sales role cannot access confidential or higher classifications.
    effect: deny
    priority: 50
    when:
      - { field: user.roles, op: contains, value: sales }
      - { field: chunk.classification, op: gte, value: confidential }
`;

export interface PolicyError {
  path: string;
  message: string;
}

export function useMonacoPolicy(host: Ref<HTMLElement | null>) {
  const errors = ref<PolicyError[]>([]);
  const parseError = ref<string | null>(null);
  const isValid = ref(false);
  const ruleCount = ref(0);

  const ajv = new Ajv({ allErrors: true, strict: false });
  addFormats(ajv);
  const validate = ajv.compile(policySchema);

  let editor: monaco.editor.IStandaloneCodeEditor | null = null;

  function toPolicyError(error: ErrorObject): PolicyError {
    return { path: error.instancePath || "(root)", message: error.message ?? "invalid" };
  }

  function validateText(text: string) {
    parseError.value = null;
    errors.value = [];
    ruleCount.value = 0;

    let parsed: unknown;
    try {
      parsed = parse(text);
    } catch (cause) {
      parseError.value = cause instanceof Error ? cause.message : String(cause);
      isValid.value = false;
      return;
    }

    const ok = validate(parsed);
    if (!ok) {
      errors.value = (validate.errors ?? []).map(toPolicyError);
      isValid.value = false;
      return;
    }

    const doc = parsed as { rules?: unknown[] };
    ruleCount.value = Array.isArray(doc.rules) ? doc.rules.length : 0;
    isValid.value = true;
  }

  function download() {
    if (!editor) return;
    const blob = new Blob([editor.getValue()], { type: "text/yaml" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "policy.yaml";
    link.click();
    URL.revokeObjectURL(url);
  }

  onMounted(() => {
    if (!host.value) return;
    editor = monaco.editor.create(host.value, {
      value: DEFAULT_POLICY,
      language: "yaml",
      theme: "vs-dark",
      minimap: { enabled: false },
      fontSize: 13,
      scrollBeyondLastLine: false,
      automaticLayout: true,
    });
    editor.getModel()?.onDidChangeContent(() => validateText(editor!.getValue()));
    validateText(DEFAULT_POLICY);
  });

  onBeforeUnmount(() => {
    editor?.dispose();
    editor = null;
  });

  return { errors, parseError, isValid, ruleCount, download };
}
