// Model picker logic: which Ollama chat model the live query path uses, plus
// pulling new models on demand. Dev-only - the endpoints self-disable in prod.
// Keeps ModelPicker.vue presentational.
import { computed, onMounted, ref } from "vue";

import { ApiError, listModels, pullModel, setModel } from "@/api/operations";
import type { DevModel } from "@/api/types";

export interface ModelPreset {
  name: string;
  label: string;
  description: string;
}

export const MODEL_PRESETS: ModelPreset[] = [
  {
    name: "llama3.2:3b",
    label: "Fast demo",
    description: "Small and quick on laptops.",
  },
  {
    name: "qwen2.5:7b",
    label: "Best default",
    description: "Stronger reasoning for the demo.",
  },
  {
    name: "mistral:7b",
    label: "Fallback",
    description: "Good general local model.",
  },
];

const OLLAMA_DOWNLOAD_URL = "https://ollama.com/download";

/** Bytes to a short human label (e.g. "4.7 GB"), for the model list. */
function formatSize(bytes: number): string {
  if (bytes <= 0) return "";
  const gb = bytes / 1_000_000_000;
  if (gb >= 1) return `${gb.toFixed(1)} GB`;
  return `${Math.round(bytes / 1_000_000)} MB`;
}

function isChatModel(model: DevModel): boolean {
  const name = model.name.toLowerCase();
  return !name.includes("embed") && !name.includes("embedding");
}

export function useModelPicker() {
  const models = ref<DevModel[]>([]);
  const activeModel = ref("");
  const isLoading = ref(false);
  const isSwitching = ref(false);
  const isPulling = ref(false);
  const installingModel = ref("");
  const error = ref("");
  const ollamaUnavailable = ref(false);

  const chatModels = computed(() => models.value.filter(isChatModel));
  const installedNames = computed(() => new Set(models.value.map((model) => model.name)));
  const hasNoModels = computed(
    () => !isLoading.value && !ollamaUnavailable.value && chatModels.value.length === 0,
  );

  function isInstalled(name: string): boolean {
    return installedNames.value.has(name);
  }

  function isActive(name: string): boolean {
    return activeModel.value === name;
  }

  function presetAction(name: string): string {
    if (installingModel.value === name) return "Installing";
    if (isActive(name)) return "Active";
    if (isInstalled(name)) return "Use";
    return "Install";
  }

  async function load() {
    isLoading.value = true;
    error.value = "";
    ollamaUnavailable.value = false;
    try {
      const data = await listModels();
      models.value = data.models;
      activeModel.value = data.active;
    } catch (caught) {
      const message = caught instanceof ApiError ? caught.message : "Could not load models";
      ollamaUnavailable.value = message.toLowerCase().includes("cannot reach ollama");
      models.value = [];
      error.value = ollamaUnavailable.value ? "" : message;
    } finally {
      isLoading.value = false;
    }
  }

  async function selectModel(name: string) {
    if (isSwitching.value || name === activeModel.value) return;
    isSwitching.value = true;
    error.value = "";
    try {
      const data = await setModel(name);
      activeModel.value = data.model;
    } catch (caught) {
      error.value = caught instanceof ApiError ? caught.message : "Could not switch model";
    } finally {
      isSwitching.value = false;
    }
  }

  async function usePreset(name: string) {
    if (isPulling.value || isSwitching.value || isActive(name)) return;
    error.value = "";
    try {
      if (!isInstalled(name)) {
        isPulling.value = true;
        installingModel.value = name;
        await pullModel(name);
        await load();
      }
      await selectModel(name);
    } catch (caught) {
      error.value = caught instanceof ApiError ? caught.message : "Could not pull model";
    } finally {
      isPulling.value = false;
      installingModel.value = "";
    }
  }

  onMounted(load);

  return {
    models,
    chatModels,
    activeModel,
    presets: MODEL_PRESETS,
    isLoading,
    isSwitching,
    isPulling,
    installingModel,
    error,
    hasNoModels,
    ollamaUnavailable,
    ollamaDownloadUrl: OLLAMA_DOWNLOAD_URL,
    formatSize,
    isInstalled,
    isActive,
    presetAction,
    load,
    selectModel,
    usePreset,
  };
}
