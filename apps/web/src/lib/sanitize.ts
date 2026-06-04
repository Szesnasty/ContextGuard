import DOMPurify, { type Config } from "dompurify";

const FORBIDDEN_TAGS = ["iframe", "object", "script", "style"];

const HTML_CONFIG: Config = {
  USE_PROFILES: { html: true },
  FORBID_TAGS: FORBIDDEN_TAGS,
  FORBID_ATTR: ["style"],
  ADD_ATTR: ["target"],
  ALLOW_DATA_ATTR: false,
};

const SVG_CONFIG: Config = {
  USE_PROFILES: { svg: true, svgFilters: true },
  FORBID_TAGS: [...FORBIDDEN_TAGS, "foreignObject"],
  FORBID_ATTR: ["style"],
  ALLOW_DATA_ATTR: false,
};

/** Sanitize markup before any v-html/innerHTML insertion. */
export function sanitizeHtml(raw: string, options: { svg?: boolean } = {}): string {
  return DOMPurify.sanitize(raw, options.svg ? SVG_CONFIG : HTML_CONFIG);
}
