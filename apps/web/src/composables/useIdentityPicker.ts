// Identity picker logic: which demo identity is active, its mint command, and
// saving a pasted token into that slot. Keeps the SFC presentational.
import { computed, ref } from "vue";

import { ApiError, mintToken } from "@/api/operations";
import { DEMO_IDENTITIES, mintCommand } from "@/lib/identities";
import { useAuthStore } from "@/stores/auth";

export function useIdentityPicker() {
  const auth = useAuthStore();
  const tokenDraft = ref("");
  const isMinting = ref(false);
  const mintError = ref("");

  const identities = DEMO_IDENTITIES;
  const activeIdentity = computed(
    () => DEMO_IDENTITIES.find((identity) => identity.sub === auth.activeSub) ?? null,
  );
  const mintHint = computed(() => mintCommand(auth.activeSub));
  const canSaveToken = computed(() => tokenDraft.value.trim().length > 0);

  function selectIdentity(sub: string) {
    auth.selectIdentity(sub);
    tokenDraft.value = "";
    mintError.value = "";
  }

  function saveToken() {
    if (!canSaveToken.value) return;
    auth.setToken(auth.activeSub, tokenDraft.value);
    tokenDraft.value = "";
  }

  function removeToken() {
    auth.setToken(auth.activeSub, "");
  }

  async function generateToken() {
    if (isMinting.value) return;
    isMinting.value = true;
    mintError.value = "";
    try {
      const minted = await mintToken(auth.activeSub);
      auth.setToken(minted.sub, minted.token);
      tokenDraft.value = "";
    } catch (error) {
      mintError.value =
        error instanceof ApiError ? error.message : "Could not generate a token";
    } finally {
      isMinting.value = false;
    }
  }

  return {
    auth,
    tokenDraft,
    isMinting,
    mintError,
    identities,
    activeIdentity,
    mintHint,
    canSaveToken,
    selectIdentity,
    saveToken,
    removeToken,
    generateToken,
  };
}
