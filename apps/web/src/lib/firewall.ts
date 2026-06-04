// Pure helpers for interpreting a GuardedContext. Kept framework-free so they
// are unit-tested directly (Vitest) without mounting a component.
import type { Chunk, ChunkDecision, GuardedContext, Outcome, RetrievedChunk } from "@/api/types";

export interface DecisionTally {
  allowed: number;
  blocked: number;
  redacted: number;
}

export function tally(guarded: GuardedContext): DecisionTally {
  const t: DecisionTally = { allowed: 0, blocked: 0, redacted: 0 };
  for (const d of guarded.decisions ?? []) {
    if (d.outcome === "allowed") t.allowed += 1;
    else if (d.outcome === "blocked") t.blocked += 1;
    else if (d.outcome === "redacted") t.redacted += 1;
  }
  return t;
}

export function outcomeClass(outcome: Outcome): string {
  switch (outcome) {
    case "allowed":
      return "tag tag--allowed";
    case "blocked":
      return "tag tag--blocked";
    case "redacted":
      return "tag tag--redacted";
    default:
      return "tag";
  }
}

/** Decisions that removed or masked a chunk (the firewall's "work"). */
export function enforced(guarded: GuardedContext): ChunkDecision[] {
  return (guarded.decisions ?? []).filter((d) => d.outcome !== "allowed");
}

/** Was anything kept out of the prompt? Drives the leak / no-leak headline. */
export function isContained(guarded: GuardedContext): boolean {
  return enforced(guarded).length > 0;
}

export function tokenReduction(guarded: GuardedContext): number {
  const before = guarded.tokens_before || 0;
  if (before === 0) return 0;
  const after = guarded.tokens_after || 0;
  return Math.max(0, Math.round(((before - after) / before) * 100));
}

/** The pre-firewall context: every retrieved chunk's text, in order. */
export function contextBefore(retrieved: RetrievedChunk[]): string {
  return retrieved.map((c) => `# ${c.id} (${c.classification})\n${c.text}`).join("\n\n");
}

/** The post-firewall context: only what survived, in order. */
export function contextAfter(guarded: GuardedContext): string {
  return (guarded.allowed_chunks ?? [])
    .map((c) => `# ${c.id} (${c.classification})\n${c.text}`)
    .join("\n\n");
}

/** A Mermaid flowchart of the firewall path: retrieved -> verdicts -> prompt. */
export function evidenceFlow(retrievedCount: number, guarded: GuardedContext): string {
  const t = tally(guarded);
  const lines = [
    "flowchart LR",
    `  R["Retrieved<br/>${retrievedCount}"]`,
    `  A["Allowed<br/>${t.allowed}"]`,
    `  B["Blocked<br/>${t.blocked}"]`,
    `  D["Redacted<br/>${t.redacted}"]`,
    `  P["Prompt<br/>${guarded.tokens_after ?? 0} tok"]`,
    "  R --> A",
    "  R --> B",
    "  R --> D",
    "  A --> P",
    "  D --> P",
    "  classDef ok fill:#d6f5dd,stroke:#3fb950,color:#1a1a1a;",
    "  classDef bad fill:#fbdcda,stroke:#f85149,color:#1a1a1a;",
    "  classDef warn fill:#fbecc8,stroke:#d29922,color:#1a1a1a;",
    "  class A,P ok;",
    "  class B bad;",
    "  class D warn;",
  ];
  return lines.join("\n");
}

const ALLOWED_HTML_TAGS = new Set([
  "a",
  "br",
  "code",
  "em",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "li",
  "ol",
  "p",
  "pre",
  "span",
  "strong",
  "table",
  "tbody",
  "td",
  "th",
  "thead",
  "tr",
  "ul",
]);

const ALLOWED_SVG_TAGS = new Set([
  "circle",
  "defs",
  "desc",
  "ellipse",
  "g",
  "line",
  "marker",
  "path",
  "polygon",
  "polyline",
  "rect",
  "svg",
  "text",
  "title",
  "tspan",
]);

const ALLOWED_ATTRS = new Set([
  "aria-hidden",
  "class",
  "cx",
  "cy",
  "d",
  "fill",
  "font-size",
  "height",
  "href",
  "id",
  "marker-end",
  "marker-start",
  "markerWidth",
  "markerHeight",
  "offset",
  "orient",
  "points",
  "r",
  "refX",
  "refY",
  "role",
  "rx",
  "ry",
  "stroke",
  "stroke-dasharray",
  "stroke-linecap",
  "stroke-linejoin",
  "stroke-width",
  "style",
  "target",
  "transform",
  "viewBox",
  "width",
  "x",
  "x1",
  "x2",
  "xlink:href",
  "xmlns",
  "y",
  "y1",
  "y2",
]);

const URL_ATTRS = new Set(["href", "src", "xlink:href"]);
const SAFE_STYLE = /^[\w\s#.:;,%()+\-"'/$]*$/;
const DROP_WITH_CONTENT = new Set(["iframe", "object", "script", "style"]);

function isSafeUrl(value: string): boolean {
  const trimmed = value.trim().toLowerCase();
  return !trimmed.startsWith("javascript:") && !trimmed.startsWith("data:text/html");
}

function isSafeStyle(value: string): boolean {
  const lowered = value.trim().toLowerCase();
  return (
    SAFE_STYLE.test(value) &&
    !lowered.includes("javascript:") &&
    !lowered.includes("expression(") &&
    !lowered.includes("@import") &&
    !lowered.includes("url(")
  );
}

function sanitizeElement(element: Element): void {
  for (const attr of [...element.attributes]) {
    const name = attr.name;
    if (name.startsWith("on") || !ALLOWED_ATTRS.has(name)) {
      element.removeAttribute(name);
      continue;
    }
    if (URL_ATTRS.has(name) && !isSafeUrl(attr.value)) {
      element.removeAttribute(name);
    }
    if (name === "style" && !isSafeStyle(attr.value)) {
      element.removeAttribute(name);
    }
  }
}

function walkAndSanitize(node: Node, allowedTags: Set<string>): void {
  for (const child of [...node.childNodes]) {
    if (child.nodeType !== Node.ELEMENT_NODE) {
      continue;
    }
    const element = child as Element;
    const tag = element.tagName.toLowerCase();
    if (!allowedTags.has(tag)) {
      if (DROP_WITH_CONTENT.has(tag)) {
        element.remove();
        continue;
      }
      element.replaceWith(...element.childNodes);
      continue;
    }
    sanitizeElement(element);
    walkAndSanitize(element, allowedTags);
  }
}

/** Sanitize HTML before it is inserted into the DOM. */
export function sanitizeHtml(raw: string, options: { svg?: boolean } = {}): string {
  const doc = document.implementation.createHTMLDocument("");
  doc.body.innerHTML = raw;
  const allowed = options.svg
    ? new Set([...ALLOWED_HTML_TAGS, ...ALLOWED_SVG_TAGS])
    : ALLOWED_HTML_TAGS;
  walkAndSanitize(doc.body, allowed);
  return doc.body.innerHTML;
}

// --- Provenance / grounding ------------------------------------------------
// The drawer answers two operator questions: "where did the answer's knowledge
// come from?" (source documents + relevance) and "which document is allowed
// where?" (the firewall outcome per chunk, for *this* identity).

/** A retrieved chunk enriched with its firewall verdict and prompt membership. */
export interface EnrichedChunk {
  id: string;
  docId: string;
  tenant: string;
  classification: string;
  text: string;
  score: number;
  outcome: Outcome;
  reasons: string[];
  policies: string[];
  /** True if the (possibly masked) chunk actually reached the model prompt. */
  inPrompt: boolean;
}

/** A source document and every chunk it contributed to this query. */
export interface DocumentGroup {
  docId: string;
  tenant: string;
  classification: string;
  /** Best (max) retrieval score across the document's chunks. */
  bestScore: number;
  chunks: EnrichedChunk[];
  /** Whether any chunk from this document reached the prompt. */
  anyInPrompt: boolean;
  /** Whether the firewall blocked or redacted any chunk from this document. */
  anyWithheld: boolean;
}

function decisionMap(guarded: GuardedContext): Map<string, ChunkDecision> {
  const m = new Map<string, ChunkDecision>();
  for (const d of guarded.decisions ?? []) m.set(d.chunk_id, d);
  return m;
}

/** Join retrieval hits with the firewall's per-chunk verdict. */
export function enrich(retrieved: RetrievedChunk[], guarded: GuardedContext): EnrichedChunk[] {
  const decisions = decisionMap(guarded);
  const allowedIds = new Set((guarded.allowed_chunks ?? []).map((c: Chunk) => c.id));
  return retrieved.map((hit) => {
    const d = decisions.get(hit.id);
    const outcome = d?.outcome ?? "allowed";
    return {
      id: hit.id,
      docId: hit.doc_id,
      tenant: hit.tenant,
      classification: hit.classification,
      text: hit.text,
      score: hit.score,
      outcome,
      reasons: d?.reasons ?? [],
      policies: d?.policies_triggered ?? [],
      inPrompt: allowedIds.has(hit.id) || outcome === "allowed" || outcome === "redacted",
    };
  });
}

/** Group enriched chunks by their source document, best-score first. */
export function groupByDocument(chunks: EnrichedChunk[]): DocumentGroup[] {
  const groups = new Map<string, DocumentGroup>();
  for (const c of chunks) {
    let g = groups.get(c.docId);
    if (!g) {
      g = {
        docId: c.docId,
        tenant: c.tenant,
        classification: c.classification,
        bestScore: c.score,
        chunks: [],
        anyInPrompt: false,
        anyWithheld: false,
      };
      groups.set(c.docId, g);
    }
    g.chunks.push(c);
    g.bestScore = Math.max(g.bestScore, c.score);
    g.anyInPrompt = g.anyInPrompt || c.inPrompt;
    g.anyWithheld = g.anyWithheld || c.outcome !== "allowed";
  }
  for (const g of groups.values()) {
    g.chunks.sort((a, b) => b.score - a.score);
  }
  return [...groups.values()].sort((a, b) => b.bestScore - a.bestScore);
}

/**
 * Minimal Markdown -> sanitized HTML renderer for document text shown in drawers.
 * Handles headings, bold, italic, bullet lists, code and line-breaks.
 * Escapes HTML first, then sanitizes the generated tag subset before insertion.
 */
export function renderMd(raw: string): string {
  const esc = raw
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  const lines = esc.split("\n");
  const out: string[] = [];
  let inList = false;

  for (const line of lines) {
    const heading = line.match(/^(#{1,3}) (.+)$/);
    const bullet = line.match(/^[-*] (.+)$/);

    if (heading) {
      if (inList) { out.push("</ul>"); inList = false; }
      const tag = `h${heading[1].length + 2}`; // # → h3, ## → h4, ### → h5
      out.push(`<${tag}>${inline(heading[2])}</${tag}>`);
    } else if (bullet) {
      if (!inList) { out.push("<ul>"); inList = true; }
      out.push(`<li>${inline(bullet[1])}</li>`);
    } else {
      if (inList) { out.push("</ul>"); inList = false; }
      const text = inline(line);
      out.push(text.trim() === "" ? "<br>" : `<p>${text}</p>`);
    }
  }

  if (inList) out.push("</ul>");
  return sanitizeHtml(out.join(""));
}

function inline(s: string): string {
  return s
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>");
}

export function classificationClass(classification: string): string {
  switch (classification) {
    case "public":
      return "tag tag--allowed";
    case "internal":
      return "tag tag--redacted";
    case "confidential":
    case "restricted":
    case "secret":
      return "tag tag--blocked";
    default:
      return "tag";
  }
}
