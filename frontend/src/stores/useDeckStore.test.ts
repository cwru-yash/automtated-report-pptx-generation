import { beforeEach, describe, expect, it } from "vitest";
import type { DeckDocument } from "../lib/decks/deck-schema";
import { useDeckStore } from "./useDeckStore";

const baseDeck: DeckDocument = {
  deck_id: "deck_test",
  title: "Test Deck",
  source_wave_id: "wave_test",
  source_project: "Test Project",
  theme: {
    name: "executive-light",
    font_family: "Aptos",
    primary_color: "#17324d",
    accent_color: "#c8a45d",
    background_color: "#f7f8f5",
    surface_color: "#ffffff",
    text_color: "#17202a",
    muted_text_color: "#5f6b7a",
  },
  slides: [
    {
      id: "slide_1",
      type: "finding",
      title: "Test Slide",
      speaker_notes: "",
      source_refs: [],
      content: [
        {
          id: "cols",
          type: "two_column",
          columns: [
            {
              width: 50,
              content: [{ id: "nested", type: "paragraph", text: "Original" }],
            },
            {
              width: 50,
              content: [{ id: "metric", type: "metric_card", label: "Score", value: "10" }],
            },
          ],
        },
      ],
    },
  ],
  metadata: {},
};

describe("useDeckStore", () => {
  beforeEach(() => {
    useDeckStore.setState({
      currentDeck: null,
      selectedSlideId: null,
      selectedBlockId: null,
      saveState: "saved",
      errorMessage: "",
    });
  });

  it("updates nested blocks by id", () => {
    useDeckStore.getState().setDeck(baseDeck);
    useDeckStore.getState().updateBlock("nested", { text: "Changed" });

    const deck = useDeckStore.getState().currentDeck;
    const columnBlock = deck?.slides[0]?.content[0];

    expect(columnBlock?.type).toBe("two_column");
    if (columnBlock?.type !== "two_column") {
      throw new Error("Expected two_column block");
    }
    expect(columnBlock.columns[0].content[0]).toMatchObject({
      id: "nested",
      text: "Changed",
    });
    expect(useDeckStore.getState().saveState).toBe("dirty");
  });
});
