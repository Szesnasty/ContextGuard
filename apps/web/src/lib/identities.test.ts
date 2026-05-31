import { describe, expect, it } from "vitest";

import { DEMO_IDENTITIES, mintCommand } from "@/lib/identities";

describe("DEMO_IDENTITIES", () => {
  it("mirrors the demo users with unique subjects", () => {
    const subs = DEMO_IDENTITIES.map((i) => i.sub);
    expect(new Set(subs).size).toBe(subs.length);
    expect(subs).toContain("sales@acme");
  });
});

describe("mintCommand", () => {
  it("builds the make token command for a subject", () => {
    expect(mintCommand("legal@acme")).toBe("make token SUB=legal@acme");
  });
});
