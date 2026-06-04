import { describe, expect, it } from "vitest";

import { ATTACK_PROMPTS } from "@/lib/corpus";
import { DEMO_IDENTITIES } from "@/lib/identities";

describe("attack prompt catalog", () => {
  it("ships a focused prompt set for every demo identity", () => {
    for (const identity of DEMO_IDENTITIES) {
      const prompts = ATTACK_PROMPTS.filter((prompt) => prompt.sub === identity.sub);

      expect(prompts.length, identity.sub).toBeGreaterThanOrEqual(5);
      expect(new Set(prompts.map((prompt) => prompt.category)).size, identity.sub).toBeGreaterThan(2);
    }
  });

  it("keeps sales and admin prompt sets different", () => {
    const titlesFor = (sub: string) =>
      ATTACK_PROMPTS.filter((prompt) => prompt.sub === sub).map((prompt) => prompt.title);

    expect(titlesFor("sales@acme")).not.toEqual(titlesFor("admin@acme"));
  });
});
