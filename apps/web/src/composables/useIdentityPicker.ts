// Identity picker logic: which demo identity is active, its mint command, and
// saving a pasted token into that slot. Keeps the SFC presentational.
import { computed, ref } from "vue";

import { DEMO_IDENTITIES, mintCommand } from "@/lib/identities";
import { useAuthStore } from "@/stores/auth";

export function useIdentityPicker() {
  const auth = useAuthStore();
  const tokenDraft = ref("");

  const identities = DEMO_IDENTITIES;
  const activeIdentity = computed(
    () => DEMO_IDENTITIES.find((identity) => identity.sub === auth.activeSub) ?? null,
  );
  const mintHint = computed(() => mintCommand(auth.activeSub));
  const canSaveToken = computed(() => tokenDraft.value.trim().length > 0);

  function selectIdentity(sub: string) {
    auth.selectIdentity(sub);
    tokenDraft.value = "";
  }

  function saveToken() {
    if (!canSaveToken.value) return;
    auth.setToken(auth.activeSub, tokenDraft.value);
    tokenDraft.value = "";
  }

  function removeToken() {
    auth.setToken(auth.activeSub, "");
  }

  return {
    auth,
    tokenDraft,
    identities,
    activeIdentity,
    mintHint,
    canSaveToken,
    selectIdentity,
    saveToken,
    removeToken,
  };
}
