// Convenience aliases over the auto-generated OpenAPI schema. These are the
// single source of truth for request/response shapes - regenerate with
// `make openapi` whenever a contracts model changes (ADR-004).
import type { components } from "./schema";

export type Chunk = components["schemas"]["Chunk"];
export type ChunkDecision = components["schemas"]["ChunkDecision"];
export type GuardRequest = components["schemas"]["GuardRequest"];
export type GuardedContext = components["schemas"]["GuardedContext"];
export type QueryRequest = components["schemas"]["QueryRequest"];
export type QueryResponse = components["schemas"]["QueryResponse"];
export type RetrievedChunk = components["schemas"]["RetrievedChunk"];
export type Outcome = components["schemas"]["Outcome"];
export type Classification = components["schemas"]["Classification"];
export type DevTokenResponse = components["schemas"]["DevTokenResponse"];
export type DevModelsResponse = components["schemas"]["DevModelsResponse"];
export type DevModel = components["schemas"]["DevModel"];
export type DevSetModelResponse = components["schemas"]["DevSetModelResponse"];
export type DevPullModelResponse = components["schemas"]["DevPullModelResponse"];
