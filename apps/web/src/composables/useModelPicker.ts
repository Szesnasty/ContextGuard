// Model picker logic: which Ollama chat model the live query path uses, plus
// pulling new models on demand. Dev-only - the endpoints self-disable in prod.
// Keeps ModelPicker.vue presentational.
import { computed, onMounted, ref } from "vue";

import { ApiError, listModels, pullModel, setModel } from "@/api/operations";
import type { DevModel } from "@/api/types";

/** Bytes to a short human label (e.g. "4.7 GB"), for the model list. */
function formatSize(bytes: number): string {
  if (bytes <= 0) return "";
  const gb = bytes / 1_000_000_000;
  if (gb >= 1) return `${gb.toFixed(1)} GB`;
  return `${Math.round(bytes / 1_000_000)} MB`;
}

export function useModelPicker() {
  const models = ref<DevModel[]>([]);
  const activeModel = ref("");
  const pullName = ref("");
  const isLoading = ref(false);
  const isSwitching = ref(false);
  const isPulling = ref(false);
  const error = ref("");

  const canPull = computed(() => pullName.value.trim().length > 0 && !isPulling.value);

  async function load() {
    isLoading.value = true;
    error.value = "";
    try {
      const data = await listModels();
      models.value = data.models;
      activeModel.value = data.active;
    } catch (caught) {
      error.value = caught instanceof ApiError ? caught.message : "Could not load models";
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

  async function pull() {
    if (!canPull.value) return;
    isPulling.value = true;
    error.value = "";
    try {
      await pullModel(pullName.value.trim());
      pullName.value = "";
      await load();
    } catch (caught) {
      error.value = caught instanceof ApiError ? caught.message : "Could not pull model";
    } finally {
      isPulling.value = false;
    }
  }

  onMounted(load);

  return {
    models,
    activeModel,
    pullName,
    isLoading,
    isSwitching,
    isPulling,
    error,
    canPull,
    formatSize,
    load,
    selectModel,
    pull,
  };
}
