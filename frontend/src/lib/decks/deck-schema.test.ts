import { describe, expect, it } from "vitest";
import fixture from "../../../../tests/fixtures/canonical_deck_document.json";
import { deckDocumentSchema } from "./deck-schema";

describe("deck schema parity", () => {
  it("accepts the canonical backend DeckDocument fixture", () => {
    const parsed = deckDocumentSchema.parse(fixture);

    expect(parsed.deck_id).toBe("canonical_deck_fixture");
    expect(parsed.slides[1].content[0].type).toBe("two_column");
  });
});
