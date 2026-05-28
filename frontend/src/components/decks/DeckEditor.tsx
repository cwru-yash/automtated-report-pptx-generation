import { useEffect, useMemo, useState } from "react";
import {
  acceptAiDeckOutlineFromWave,
  createDeckFromWave,
  deckHtmlPreviewUrl,
  exportDeckPptx,
  fetchDeck,
  fetchDemoDeck,
  generateAiDeckOutlineFromWave,
  saveDeck,
} from "../../lib/decks/api";
import { createDebouncedAction } from "../../lib/decks/debounce";
import type { DeckDocument, DeckOutline } from "../../lib/decks/deck-schema";
import { useDeckStore } from "../../stores/useDeckStore";
import { useGenerationStore } from "../../stores/useGenerationStore";
import { usePromptStore } from "../../stores/usePromptStore";
import { PresentationMode } from "./preview/PresentationMode";
import { SlideCanvas } from "./SlideCanvas";
import { SlideSidebar } from "./SlideSidebar";
import { ThemePanel } from "./panels/ThemePanel";

const AUTOSAVE_DELAY_MS = 1800;
type ExportStatus = "idle" | "loading" | "error";
type OutlineStatus = "idle" | "loading" | "ready" | "error";
type OutlineAcceptStatus = "idle" | "loading" | "error";

function editMarker(deck: DeckDocument) {
  return typeof deck.metadata.edited_at === "string" ? deck.metadata.edited_at : "";
}

export function DeckEditor() {
  const [previewOpen, setPreviewOpen] = useState(false);
  const [createdDeckLink, setCreatedDeckLink] = useState<{ deckId: string; url: string } | null>(null);
  const [exportStatus, setExportStatus] = useState<ExportStatus>("idle");
  const [exportError, setExportError] = useState("");
  const [outlineStatus, setOutlineStatus] = useState<OutlineStatus>("idle");
  const [outlineError, setOutlineError] = useState("");
  const [aiOutline, setAiOutline] = useState<DeckOutline | null>(null);
  const [outlineAcceptStatus, setOutlineAcceptStatus] = useState<OutlineAcceptStatus>("idle");
  const [outlineAcceptError, setOutlineAcceptError] = useState("");
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

  async function handleGenerateAiOutline() {
    if (!reportSourceId.trim()) {
      setOutlineStatus("error");
      setOutlineError("Enter a wave ID before generating an AI outline.");
      return;
    }
    setOutlineStatus("loading");
    setOutlineError("");
    setAiOutline(null);
    try {
      const outline = await generateAiDeckOutlineFromWave(reportSourceId.trim());
      setAiOutline(outline);
      setOutlineStatus("ready");
      setOutlineAcceptError("");
      setOutlineAcceptStatus("idle");
    } catch (error) {
      const message = error instanceof Error ? error.message : "AI outline generation failed";
      setOutlineStatus("error");
      setOutlineError(message);
    }
  }

  async function handleAcceptAiOutline() {
    if (!aiOutline) {
      setOutlineAcceptStatus("error");
      setOutlineAcceptError("Generate and review an AI outline before creating a deck.");
      return;
    }
    if (!reportSourceId.trim()) {
      setOutlineAcceptStatus("error");
      setOutlineAcceptError("Enter a wave ID before creating a deck from an AI outline.");
      return;
    }
    setCreatedDeckLink(null);
    setOutlineAcceptStatus("loading");
    setOutlineAcceptError("");
    try {
      const createdDeck = await acceptAiDeckOutlineFromWave(reportSourceId.trim(), aiOutline);
      setDeck(createdDeck);
      setReady();
      const url = `/decks/editor/${createdDeck.deck_id}`;
      setCreatedDeckLink({ deckId: createdDeck.deck_id, url });
      setOutlineAcceptStatus("idle");
      window.history.replaceState(null, "", url);
    } catch (error) {
      const message = error instanceof Error ? error.message : "AI outline acceptance failed";
      setOutlineAcceptStatus("error");
      setOutlineAcceptError(message);
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
          <button type="button" onClick={handleGenerateAiOutline} disabled={outlineStatus === "loading"}>
            {outlineStatus === "loading" ? "Generating Outline..." : "Generate AI Outline"}
          </button>
          {!aiOutline ? (
            <button type="button" disabled>
              Create Deck from AI Outline
            </button>
          ) : null}
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
      {outlineStatus === "error" ? <div className="error-banner">AI outline failed: {outlineError}</div> : null}
      {outlineAcceptStatus === "error" ? (
        <div className="error-banner">AI outline acceptance failed: {outlineAcceptError}</div>
      ) : null}
      {aiOutline ? (
        <AIOutlinePreview
          outline={aiOutline}
          onAccept={handleAcceptAiOutline}
          acceptStatus={outlineAcceptStatus}
        />
      ) : null}

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

function AIOutlinePreview({
  outline,
  onAccept,
  acceptStatus,
}: {
  outline: DeckOutline;
  onAccept: () => void;
  acceptStatus: OutlineAcceptStatus;
}) {
  return (
    <section className="ai-outline-preview" aria-label="AI outline preview">
      <div className="outline-head">
        <div>
          <p className="eyebrow">AI Outline Preview</p>
          <h2>{outline.deck_title}</h2>
        </div>
        <div className="outline-actions">
          <span>{outline.slides.length} slides</span>
          <button type="button" onClick={onAccept} disabled={acceptStatus === "loading"}>
            {acceptStatus === "loading" ? "Creating Deck..." : "Create Deck from AI Outline"}
          </button>
        </div>
      </div>
      <dl className="outline-meta">
        <div>
          <dt>Audience</dt>
          <dd>{outline.audience}</dd>
        </div>
        <div>
          <dt>Objective</dt>
          <dd>{outline.objective}</dd>
        </div>
      </dl>
      {outline.warnings.length ? (
        <div className="outline-warnings">
          <strong>Warnings</strong>
          <ul>
            {outline.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="outline-slide-grid">
        {outline.slides.map((slide, index) => (
          <article className="outline-slide-card" key={`${slide.title}-${index}`}>
            <span>Slide {index + 1}</span>
            <h3>{slide.title}</h3>
            <p><strong>Purpose:</strong> {slide.purpose}</p>
            <p><strong>Message:</strong> {slide.key_message}</p>
            <p><strong>Visual:</strong> {slide.suggested_visual_type}</p>
            <p><strong>Evidence:</strong> {slide.evidence_refs.length ? slide.evidence_refs.join(", ") : "None"}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
