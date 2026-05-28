import { act, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DeckDocument } from "../../lib/decks/deck-schema";
import { useDeckStore } from "../../stores/useDeckStore";
import { useGenerationStore } from "../../stores/useGenerationStore";
import { usePromptStore } from "../../stores/usePromptStore";
import { DeckEditor } from "./DeckEditor";

const apiMocks = vi.hoisted(() => ({
  createDeckFromWave: vi.fn(),
  fetchDeck: vi.fn(),
  fetchDemoDeck: vi.fn(),
  saveDeck: vi.fn(),
}));

vi.mock("../../lib/decks/api", () => apiMocks);

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason?: unknown) => void;
};

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

const baseDeck: DeckDocument = {
  deck_id: "deck_autosave",
  title: "Autosave Deck",
  source_wave_id: "wave_autosave",
  source_project: "Autosave Project",
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
      type: "title",
      title: "Autosave Deck",
      speaker_notes: "",
      source_refs: [],
      content: [
        { id: "heading", type: "heading", text: "Autosave Deck", level: 1 },
        { id: "paragraph", type: "paragraph", text: "Original text" },
      ],
    },
  ],
  metadata: {},
};

describe("DeckEditor autosave", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useDeckStore.setState({
      currentDeck: null,
      selectedSlideId: null,
      selectedBlockId: null,
      saveState: "saved",
      errorMessage: "",
    });
    useGenerationStore.setState({
      generationStatus: "idle",
      activeStep: "",
      errors: [],
      outline: null,
    });
    usePromptStore.setState({
      latestUserPrompt: "",
      reportSourceId: "",
      generationMode: "from_wave",
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("does not mark newer edits saved when an older save resolves later", async () => {
    const firstSave = deferred<DeckDocument>();
    apiMocks.fetchDemoDeck.mockResolvedValue({ ...baseDeck });
    apiMocks.saveDeck.mockReturnValue(firstSave.promise);

    render(<DeckEditor />);

    await waitFor(() => {
      expect(useDeckStore.getState().currentDeck?.deck_id).toBe("deck_autosave");
    });

    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-05-27T00:00:00.000Z"));

    act(() => {
      useDeckStore.getState().updateBlock("paragraph", { text: "First edit" });
    });
    await act(async () => {
      vi.advanceTimersByTime(1800);
      await Promise.resolve();
    });

    expect(apiMocks.saveDeck).toHaveBeenCalledTimes(1);
    expect(useDeckStore.getState().saveState).toBe("saving");

    vi.setSystemTime(new Date("2026-05-27T00:00:02.000Z"));
    act(() => {
      useDeckStore.getState().updateBlock("paragraph", { text: "Second edit" });
    });

    expect(useDeckStore.getState().saveState).toBe("dirty");

    await act(async () => {
      firstSave.resolve({ ...baseDeck });
      await Promise.resolve();
    });

    expect(useDeckStore.getState().currentDeck?.slides[0].content[1]).toMatchObject({
      id: "paragraph",
      text: "Second edit",
    });
    expect(useDeckStore.getState().saveState).toBe("dirty");
  });
});
