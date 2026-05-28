import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import fixture from "../../../../tests/fixtures/canonical_deck_document.json";
import { deckDocumentSchema } from "../../lib/decks/deck-schema";
import { ContentRenderer } from "./ContentRenderer";

describe("ContentRenderer", () => {
  it("renders the canonical DeckDocument fixture without crashing", () => {
    const deck = deckDocumentSchema.parse(fixture);

    render(
      <>
        {deck.slides.flatMap((slide) =>
          slide.content.map((block) => <ContentRenderer block={block} key={`${slide.id}-${block.id}`} />)
        )}
      </>
    );

    expect(screen.getAllByDisplayValue("Canonical Evidence Deck").length).toBeGreaterThan(0);
    expect(screen.getByText("chart_6")).toBeTruthy();
    expect(screen.getByDisplayValue("Evidence score")).toBeTruthy();
    expect(screen.getByText("Activity")).toBeTruthy();
    expect(screen.getByText("US10")).toBeTruthy();
    expect(screen.getByDisplayValue(/Any new numeric claim must be present/)).toBeTruthy();
  });

  it("renders a safe fallback for unknown blocks", () => {
    render(<ContentRenderer block={{ id: "bad", type: "mystery" }} />);

    expect(screen.getByRole("alert").textContent).toContain("Unsupported block type");
  });
});
