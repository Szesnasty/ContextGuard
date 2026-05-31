// Domain operations over the typed client. These wrap the two API calls the
// dashboard's firewall story needs:
//
//   1. /v1/query  - full RAG: retrieval + model answer. Deliberately a
//      pass-through guard, so this is the *pre-firewall* (leaky) baseline.
//   2. /v1/guard  - scan-only: adjudicate the supplied chunks against the
//      active policy. This is the firewall verdict (allowed/blocked/redacted).
//
// The console runs (1) to get retrieval + answer, then feeds those chunks into
// (2) to show what the firewall does to them. No identity is sent in the body
// (ADR-015); the token carries it.
import { api, describeError } from "./client";
import type { Chunk, GuardedContext, QueryResponse, RetrievedChunk } from "./types";
import type {
  DevModelsResponse,
  DevPullModelResponse,
  DevSetModelResponse,
  DevTokenResponse,
} from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** A retrieval hit lacks enrichment spans; the firewall still judges tenant +
 *  classification. Map it onto the Chunk shape /v1/guard expects. */
export function retrievedToChunk(hit: RetrievedChunk): Chunk {
  return {
    id: hit.id,
    doc_id: hit.doc_id,
    tenant: hit.tenant,
    text: hit.text,
    classification: hit.classification,
    metadata: hit.metadata ?? {},
    pii_spans: [],
    secret_spans: [],
    risk_signals: [],
  };
}

export async function runQuery(query: string, k: number): Promise<QueryResponse> {
  const { data, error, response } = await api.POST("/v1/query", {
    body: { query, k },
  });
  if (error || !data) {
    throw new ApiError(describeError(error, response.status), response.status);
  }
  return data;
}

export async function guardChunks(query: string, chunks: Chunk[]): Promise<GuardedContext> {
  const { data, error, response } = await api.POST("/v1/guard", {
    body: { query, candidate_chunks: chunks },
  });
  if (error || !data) {
    throw new ApiError(describeError(error, response.status), response.status);
  }
  return data;
}

/** Mint a signed demo token for `sub` (dev-only endpoint; disabled in prod). The
 *  request carries no auth - it is the bootstrap that *produces* a token. */
export async function mintToken(sub: string): Promise<DevTokenResponse> {
  const { data, error, response } = await api.POST("/v1/dev/token", {
    body: { sub },
  });
  if (error || !data) {
    throw new ApiError(describeError(error, response.status), response.status);
  }
  return data;
}

/** List the chat models installed in the local Ollama plus the active one
 *  (dev-only; disabled in prod). */
export async function listModels(): Promise<DevModelsResponse> {
  // openapi-fetch types a no-parameter GET (no 4xx in the schema) as `never`,
  // so we can't read `response.status` here - the error body carries the reason.
  const { data, error } = await api.GET("/v1/dev/models");
  if (error || !data) {
    throw new ApiError(describeError(error));
  }
  return data;
}

/** Switch the model the live query path uses (dev-only). */
export async function setModel(model: string): Promise<DevSetModelResponse> {
  const { data, error, response } = await api.POST("/v1/dev/model", {
    body: { model },
  });
  if (error || !data) {
    throw new ApiError(describeError(error, response.status), response.status);
  }
  return data;
}

/** Download a model into the local Ollama. Blocks until the pull finishes. */
export async function pullModel(model: string): Promise<DevPullModelResponse> {
  const { data, error, response } = await api.POST("/v1/dev/models/pull", {
    body: { model },
  });
  if (error || !data) {
    throw new ApiError(describeError(error, response.status), response.status);
  }
  return data;
}
