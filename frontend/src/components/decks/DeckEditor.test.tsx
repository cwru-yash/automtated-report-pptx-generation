import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DeckDocument } from "../../lib/decks/deck-schema";
import { useDeckStore } from "../../stores/useDeckStore";
import { useGenerationStore } from "../../stores/useGenerationStore";
import { usePromptStore } from "../../stores/usePromptStore";
import { DeckEditor } from "./DeckEditor";

const apiMocks = vi.hoisted(() => ({
  createDeckFromWave: vi.fn(),
  deckHtmlPreviewUrl: vi.fn(),
  deckPptxExportUrl: vi.fn(),
  exportDeckPptx: vi.fn(),
  fetchDeck: vi.fn(),
  fetchDemoDeck: vi.fn(),
  generateAiDeckOutlineFromWave: vi.fn(),
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
    window.history.replaceState(null, "", "/decks/editor");
    apiMocks.deckHtmlPreviewUrl.mockReturnValue("/api/v1/decks/deck_autosave/preview/html");
    apiMocks.deckPptxExportUrl.mockReturnValue("/api/v1/decks/deck_autosave/export/pptx");
    apiMocks.exportDeckPptx.mockResolvedValue(new Blob(["pptx"]));
    apiMocks.generateAiDeckOutlineFromWave.mockResolvedValue({
      deck_title: "AI Suggested Outline",
      audience: "executive stakeholders",
      objective: "Preview an AI outline only.",
      source_wave_id: "DEMO_WAVE_001",
      warnings: ["Slides missing evidence refs: Market context"],
      slides: [
        {
          title: "Executive setup",
          purpose: "Open the story.",
          key_message: "The wave has enough evidence for an outline.",
          evidence_refs: ["finding_1"],
          suggested_visual_type: "executive_summary",
        },
        {
          title: "Priority finding",
          purpose: "Show the most important signal.",
          key_message: "The first finding anchors the deck.",
          evidence_refs: ["finding_1", "chart_6"],
          suggested_visual_type: "insight_slide",
        },
      ],
    });
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

  it("loads a persisted deck when the editor URL includes a deck id", async () => {
    window.history.replaceState(null, "", "/decks/editor/deck_from_url");
    apiMocks.fetchDeck.mockResolvedValue({
      ...baseDeck,
      deck_id: "deck_from_url",
      title: "Loaded From URL",
    });

    render(<DeckEditor />);

    await waitFor(() => {
      expect(apiMocks.fetchDeck).toHaveBeenCalledWith("deck_from_url");
    });
    expect(screen.getByText("Loaded From URL")).toBeTruthy();
    expect(useDeckStore.getState().currentDeck?.deck_id).toBe("deck_from_url");
  });

  it("creates an editable deck from a wave and shows an open link", async () => {
    const createdDeck = {
      ...baseDeck,
      deck_id: "deck_created_from_wave",
      title: "Created From Wave",
    };
    apiMocks.fetchDemoDeck.mockResolvedValue({ ...baseDeck });
    apiMocks.createDeckFromWave.mockResolvedValue(createdDeck);

    render(<DeckEditor />);

    await waitFor(() => {
      expect(useDeckStore.getState().currentDeck?.deck_id).toBe("deck_autosave");
    });

    fireEvent.change(screen.getByLabelText("Wave ID"), {
      target: { value: "DEMO_WAVE_001" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create editable deck/i }));

    await waitFor(() => {
      expect(apiMocks.createDeckFromWave).toHaveBeenCalledWith("DEMO_WAVE_001");
    });
    expect(useDeckStore.getState().currentDeck?.deck_id).toBe("deck_created_from_wave");
    expect(window.location.pathname).toBe("/decks/editor/deck_created_from_wave");
    expect(screen.getByText("deck_created_from_wave")).toBeTruthy();
    expect(screen.getByRole("link", { name: /open created deck/i }).getAttribute("href")).toBe(
      "/decks/editor/deck_created_from_wave"
    );
  });

  it("shows the backend data-quality error when deck creation is blocked", async () => {
    apiMocks.fetchDemoDeck.mockResolvedValue({ ...baseDeck });
    apiMocks.createDeckFromWave.mockRejectedValue(
      new Error("Wave has no gold activity rows; deck generation blocked.")
    );

    render(<DeckEditor />);

    await waitFor(() => {
      expect(useDeckStore.getState().currentDeck?.deck_id).toBe("deck_autosave");
    });

    fireEvent.change(screen.getByLabelText("Wave ID"), {
      target: { value: "BAD_WAVE" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create editable deck/i }));

    expect(await screen.findByText(/Wave has no gold activity rows/)).toBeTruthy();
  });

  it("shows an export error and resets the export loading state", async () => {
    apiMocks.fetchDemoDeck.mockResolvedValue({ ...baseDeck });
    apiMocks.exportDeckPptx.mockRejectedValue(new Error("Template not found: missing_template"));

    render(<DeckEditor />);

    await waitFor(() => {
      expect(useDeckStore.getState().currentDeck?.deck_id).toBe("deck_autosave");
    });

    fireEvent.click(screen.getByRole("button", { name: /export ppt/i }));

    expect(await screen.findByText(/PPT export failed: Template not found/)).toBeTruthy();
    const exportButton = screen.getByRole("button", { name: /export ppt/i }) as HTMLButtonElement;
    expect(exportButton.disabled).toBe(false);
  });

  it("renders AI outline cards returned for a wave", async () => {
    apiMocks.fetchDemoDeck.mockResolvedValue({ ...baseDeck });

    render(<DeckEditor />);

    await waitFor(() => {
      expect(useDeckStore.getState().currentDeck?.deck_id).toBe("deck_autosave");
    });

    fireEvent.change(screen.getByLabelText("Wave ID"), {
      target: { value: "DEMO_WAVE_001" },
    });
    fireEvent.click(screen.getByRole("button", { name: /generate ai outline/i }));

    await waitFor(() => {
      expect(apiMocks.generateAiDeckOutlineFromWave).toHaveBeenCalledWith("DEMO_WAVE_001");
    });
    expect(await screen.findByText("AI Suggested Outline")).toBeTruthy();
    expect(screen.getByText("Preview an AI outline only.")).toBeTruthy();
    expect(screen.getByText("Executive setup")).toBeTruthy();
    expect(screen.getByText("Priority finding")).toBeTruthy();
    expect(screen.getByText(/finding_1, chart_6/)).toBeTruthy();
    expect(screen.getByText(/Slides missing evidence refs/)).toBeTruthy();
  });

  it("shows disabled-provider error from AI outline generation", async () => {
    apiMocks.fetchDemoDeck.mockResolvedValue({ ...baseDeck });
    apiMocks.generateAiDeckOutlineFromWave.mockRejectedValue(
      new Error("AI outline provider is not configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY to enable it.")
    );

    render(<DeckEditor />);

    await waitFor(() => {
      expect(useDeckStore.getState().currentDeck?.deck_id).toBe("deck_autosave");
    });

    fireEvent.change(screen.getByLabelText("Wave ID"), {
      target: { value: "DEMO_WAVE_001" },
    });
    fireEvent.click(screen.getByRole("button", { name: /generate ai outline/i }));

    expect(await screen.findByText(/AI outline provider is not configured/)).toBeTruthy();
  });

  it("shows backend validation error from AI outline generation", async () => {
    apiMocks.fetchDemoDeck.mockResolvedValue({ ...baseDeck });
    apiMocks.generateAiDeckOutlineFromWave.mockRejectedValue(
      new Error("AI outline output failed schema validation")
    );

    render(<DeckEditor />);

    await waitFor(() => {
      expect(useDeckStore.getState().currentDeck?.deck_id).toBe("deck_autosave");
    });

    fireEvent.change(screen.getByLabelText("Wave ID"), {
      target: { value: "DEMO_WAVE_001" },
    });
    fireEvent.click(screen.getByRole("button", { name: /generate ai outline/i }));

    expect(await screen.findByText(/AI outline output failed schema validation/)).toBeTruthy();
  });
});
