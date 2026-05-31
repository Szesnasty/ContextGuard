// Auth store as a token "wallet": one Bearer token per demo identity slot. The
// operator pastes a token minted with `make token SUB=<sub>`; the picker just
// switches which slot is active. The token is the *only* identity input sent to
// the API (ADR-015) - we decode it purely to display and verify the slot.
import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { setTokenProvider } from "@/api/client";
import { DEMO_IDENTITIES } from "@/lib/identities";

const STORAGE_KEY = "cg.wallet";
const ACTIVE_KEY = "cg.activeSub";

export interface DecodedIdentity {
  sub?: string;
  tenant?: string;
  role?: string;
  purpose?: string;
}

/** Decode a JWT payload without verifying it (display only). */
export function decodeIdentity(token: string): DecodedIdentity | null {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  try {
    const json = atob(parts[1].replace(/-/g, "+").replace(/_/g, "/"));
    const claims = JSON.parse(json) as Record<string, unknown>;
    const pick = (k: string) => (typeof claims[k] === "string" ? (claims[k] as string) : undefined);
    return { sub: pick("sub"), tenant: pick("tenant"), role: pick("role"), purpose: pick("purpose") };
  } catch {
    return null;
  }
}

function loadWallet(): Record<string, string> {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}") as Record<string, string>;
  } catch {
    return {};
  }
}

export const useAuthStore = defineStore("auth", () => {
  const wallet = ref<Record<string, string>>(loadWallet());
  const activeSub = ref<string>(localStorage.getItem(ACTIVE_KEY) ?? DEMO_IDENTITIES[0]?.sub ?? "");

  // Feed the typed client the active slot's token (read lazily per request).
  setTokenProvider(() => wallet.value[activeSub.value] || null);

  const token = computed<string>(() => wallet.value[activeSub.value] ?? "");
  const isAuthenticated = computed(() => token.value.length > 0);
  const identity = computed<DecodedIdentity | null>(() =>
    token.value ? decodeIdentity(token.value) : null,
  );

  /** True when the active token's decoded sub disagrees with the chosen slot. */
  const slotMismatch = computed(() => {
    const id = identity.value;
    return Boolean(id?.sub && activeSub.value && id.sub !== activeSub.value);
  });

  const label = computed(() => {
    const id = identity.value;
    if (!token.value) return `${activeSub.value || "no identity"} · no token`;
    if (!id?.sub) return "unknown identity";
    return `${id.sub} · ${id.role ?? "?"} @ ${id.tenant ?? "?"}`;
  });

  function persist() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(wallet.value));
    localStorage.setItem(ACTIVE_KEY, activeSub.value);
  }

  function setToken(sub: string, next: string): void {
    const trimmed = next.trim();
    if (trimmed) {
      wallet.value = { ...wallet.value, [sub]: trimmed };
    } else {
      const copy = { ...wallet.value };
      delete copy[sub];
      wallet.value = copy;
    }
    persist();
  }

  function selectIdentity(sub: string): void {
    activeSub.value = sub;
    persist();
  }

  return {
    wallet,
    activeSub,
    token,
    identity,
    isAuthenticated,
    slotMismatch,
    label,
    setToken,
    selectIdentity,
  };
});
