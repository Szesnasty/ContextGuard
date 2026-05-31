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
