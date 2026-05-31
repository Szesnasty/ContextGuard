// The typed HTTP client. One openapi-fetch instance, fully typed against the
// generated OpenAPI schema, with a middleware that attaches the demo Bearer
// token (ADR-015: identity is carried in the token, never in the body).
//
// The base URL is empty by default so requests are same-origin and the Vite dev
// proxy forwards /v1 to the API (uvicorn on :8000). Set VITE_API_BASE to talk to
// an absolute origin instead.
import createClient, { type Middleware } from "openapi-fetch";

import type { paths } from "./schema";

/** Reads the current Bearer token. Set by the auth store; null when unset. */
let tokenProvider: () => string | null = () => null;

/** Wire the token source. Called once from the auth store on creation. */
export function setTokenProvider(provider: () => string | null): void {
  tokenProvider = provider;
}

const authMiddleware: Middleware = {
  onRequest({ request }) {
    const token = tokenProvider();
    if (token) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  },
};

export const api = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_BASE || "",
});

api.use(authMiddleware);

/** Normalize an openapi-fetch error payload into a readable message. */
export function describeError(error: unknown, status?: number): string {
  if (error && typeof error === "object" && "detail" in error) {
    const detail = (error as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object" && "error" in detail) {
      return String((detail as { error: unknown }).error);
    }
    return JSON.stringify(detail);
  }
  if (status === 401) return "Unauthorized — paste a valid token (make token SUB=...).";
  if (typeof error === "string") return error;
  return status ? `Request failed (HTTP ${status}).` : "Request failed.";
}
