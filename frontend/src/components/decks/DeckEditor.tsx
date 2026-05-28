import { useEffect, useMemo, useState } from "react";
import { createDeckFromWave, deckHtmlPreviewUrl, exportDeckPptx, fetchDeck, fetchDemoDeck, saveDeck } from "../../lib/decks/api";
import { createDebouncedAction } from "../../lib/decks/debounce";
import type { DeckDocument } from "../../lib/decks/deck-schema";
import { useDeckStore } from "../../stores/useDeckStore";
import { useGenerationStore } from "../../stores/useGenerationStore";
import { usePromptStore } from "../../stores/usePromptStore";
import { PresentationMode } from "./preview/PresentationMode";
import { SlideCanvas } from "./SlideCanvas";
import { SlideSidebar } from "./SlideSidebar";
import { ThemePanel } from "./panels/ThemePanel";

const AUTOSAVE_DELAY_MS = 1800;
type ExportStatus = "idle" | "loading" | "error";

function editMarker(deck: DeckDocument) {
  return typeof deck.metadata.edited_at === "string" ? deck.metadata.edited_at : "";
}

export function DeckEditor() {
  const [previewOpen, setPreviewOpen] = useState(false);
  const [createdDeckLink, setCreatedDeckLink] = useState<{ deckId: string; url: string } | null>(null);
  const [exportStatus, setExportStatus] = useState<ExportStatus>("idle");
  const [exportError, setExportError] = useState("");
  const deck = useDeckStore((state) => state.currentDeck);
  const selectedSlideId = useDeckStore((state) => state.selectedSlideId);
  const saveState = useDeckStore((state) => state.saveState);
  const errorMessage = useDeckStore((state) => state.errorMessage);
  const setDeck = useDeckStore((state) => state.setDeck);
  const setSaveState = useDeckStore((state) => state.setSaveState);
  const reportSourceId = usePromptStore((state) => state.reportSourceId);
  const setReportSourceId = usePromptStore((state) => state.setReportSourceId);
  const generationStatus = useGenerationStore((state) => state.generationStatus);
  const activeStep = useGenerationStore((state) => state.activeStep);
  const generationErrors = useGenerationStore((state) => state.errors);
  const setLoading = useGenerationStore((state) => state.setLoading);
  const setReady = useGenerationStore((state) => state.setReady);
  const setError = useGenerationStore((state) => state.setError);

  const selectedSlide = useMemo(
    () => deck?.slides.find((slide) => slide.id === selectedSlideId) ?? deck?.slides[0],
    [deck, selectedSlideId]
  );

  useEffect(() => {
    const pathParts = window.location.pathname.split("/").filter(Boolean);
    const deckId = pathParts[2];
    setLoading("Loading deck");
    const loader = deckId ? fetchDeck(deckId) : fetchDemoDeck();
    loader
      .then((loadedDeck) => {
        setDeck(loadedDeck);
        setReady();
      })
      .catch((error: unknown) => {
        const message = error instanceof Error ? error.message : "Unable to load deck";
        setError(message);
      });
  }, [setDeck, setError, setLoading, setReady]);

  useEffect(() => {
    if (!deck || saveState !== "dirty") {
      return;
    }
    const debounced = createDebouncedAction<DeckDocument>(AUTOSAVE_DELAY_MS, (draftDeck) => {
      const draftEditMarker = editMarker(draftDeck);
      setSaveState("saving");
      saveDeck(draftDeck)
        .then(() => {
          const latestDeck = useDeckStore.getState().currentDeck;
          if (latestDeck && editMarker(latestDeck) === draftEditMarker) {
            setSaveState("saved");
          }
        })
        .catch((error: unknown) => {
          const message = error instanceof Error ? error.message : "Autosave failed";
          const latestDeck = useDeckStore.getState().currentDeck;
          if (latestDeck && editMarker(latestDeck) === draftEditMarker) {
            setSaveState("error", message);
          }
        });
    });
    debounced.trigger(deck);
    return () => debounced.cancel();
  }, [deck, saveState, setSaveState]);

  async function handleCreateFromWave() {
    if (!reportSourceId.trim()) {
      setError("Enter a wave ID before generating.");
      return;
    }
    setCreatedDeckLink(null);
    setLoading("Creating deck from wave");
    try {
      const createdDeck = await createDeckFromWave(reportSourceId.trim());
      setDeck(createdDeck);
      setReady();
      const url = `/decks/editor/${createdDeck.deck_id}`;
      setCreatedDeckLink({ deckId: createdDeck.deck_id, url });
      window.history.replaceState(null, "", url);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Deck generation failed";
      setError(message);
    }
  }

  async function handleExportPptx() {
    if (!deck) {
      return;
    }
    setExportStatus("loading");
    setExportError("");
    try {
      const blob = await exportDeckPptx(deck.deck_id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${deck.deck_id}.pptx`;
      document.body.append(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setExportStatus("idle");
    } catch (error) {
      const message = error instanceof Error ? error.message : "PPT export failed";
      setExportStatus("error");
      setExportError(message);
    }
  }

  function handleOpenHtmlPreview() {
    if (!deck) {
      return;
    }
    window.open(deckHtmlPreviewUrl(deck.deck_id), "_blank", "noopener,noreferrer");
  }

  if (previewOpen && deck) {
    return <PresentationMode deck={deck} onClose={() => setPreviewOpen(false)} />;
  }

  return (
    <div className="deck-editor-shell">
      <header className="deck-toolbar">
        <div>
          <p className="eyebrow">Report-to-Deck Studio</p>
          <h1>{deck?.title || "Loading deck"}</h1>
        </div>
        <div className="toolbar-actions">
          <input
            value={reportSourceId}
            onChange={(event) => setReportSourceId(event.target.value)}
            placeholder="Completed wave ID"
            aria-label="Wave ID"
          />
          <button type="button" onClick={handleCreateFromWave} disabled={generationStatus === "loading"}>
            Create Editable Deck
          </button>
          <button type="button" onClick={handleExportPptx} disabled={!deck || exportStatus === "loading"}>
            {exportStatus === "loading" ? "Exporting..." : "Export PPT"}
          </button>
          <button type="button" onClick={handleOpenHtmlPreview} disabled={!deck}>
            HTML Preview
          </button>
          <button type="button" onClick={() => setPreviewOpen(true)} disabled={!deck}>
            Preview
          </button>
          <span className={`save-pill ${saveState}`}>{saveState}</span>
        </div>
      </header>

      {errorMessage ? <div className="error-banner">{errorMessage}</div> : null}
      {generationStatus === "loading" ? <div className="status-banner">{activeStep}...</div> : null}
      {generationStatus === "error" ? (
        <div className="error-banner">{generationErrors.at(-1) || "Generation failed."}</div>
      ) : null}
      {createdDeckLink ? (
        <div className="success-banner">
          Created deck <code>{createdDeckLink.deckId}</code>.{" "}
          <a href={createdDeckLink.url}>Open created deck</a>
        </div>
      ) : null}
      {exportStatus === "error" ? <div className="error-banner">PPT export failed: {exportError}</div> : null}

      {deck ? (
        <div className="editor-grid">
          <SlideSidebar slides={deck.slides} />
          <SlideCanvas slide={selectedSlide} />
          <ThemePanel />
        </div>
      ) : (
        <div className="loading-panel">Preparing editor...</div>
      )}
    </div>
  );
}
