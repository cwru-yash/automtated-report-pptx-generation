import {
  aiOutlineResponseSchema,
  deckDocumentSchema,
  type DeckDocument,
  type DeckOutline,
  type DeckProjectResponse,
} from "./deck-schema";

async function readErrorMessage(response: Response): Promise<string> {
  const text = await response.text();
  if (!text) {
    return `${response.status} ${response.statusText}`;
  }
  try {
    const parsed = JSON.parse(text) as { detail?: unknown };
    if (typeof parsed.detail === "string") {
      return parsed.detail;
    }
    if (Array.isArray(parsed.detail)) {
      return parsed.detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return JSON.stringify(item);
        })
        .join("; ");
    }
  } catch {
    return text;
  }
  return text;
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  return response.json() as Promise<T>;
}

function editorTokenHeader(): HeadersInit {
  const token = window.localStorage.getItem("deck-editor-token");
  return token ? { "X-Deck-Edit-Token": token } : {};
}

export async function fetchDemoDeck(): Promise<DeckDocument> {
  const data = await readJson<DeckProjectResponse>(await fetch("/api/v1/decks/demo"));
  return deckDocumentSchema.parse(data.deck_json);
}

export async function fetchDeck(deckId: string): Promise<DeckDocument> {
  const data = await readJson<DeckProjectResponse>(await fetch(`/api/v1/decks/${deckId}`));
  return deckDocumentSchema.parse(data.deck_json);
}

export async function createDeckFromWave(waveId: string): Promise<DeckDocument> {
  const data = await readJson<DeckProjectResponse>(
    await fetch("/api/v1/decks/from-wave", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...editorTokenHeader(),
      },
      body: JSON.stringify({ wave_id: waveId }),
    })
  );
  return deckDocumentSchema.parse(data.deck_json);
}

export async function generateAiDeckOutlineFromWave(waveId: string): Promise<DeckOutline> {
  const data = await readJson<unknown>(
    await fetch("/api/v1/decks/from-wave/outline/ai", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...editorTokenHeader(),
      },
      body: JSON.stringify({ wave_id: waveId }),
    })
  );
  return aiOutlineResponseSchema.parse(data).outline;
}

export async function acceptAiDeckOutlineFromWave(
  waveId: string,
  outline: DeckOutline
): Promise<DeckDocument> {
  const data = await readJson<DeckProjectResponse>(
    await fetch("/api/v1/decks/from-wave/outline/accept", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...editorTokenHeader(),
      },
      body: JSON.stringify({ wave_id: waveId, outline }),
    })
  );
  return deckDocumentSchema.parse(data.deck_json);
}

export async function saveDeck(deck: DeckDocument): Promise<DeckDocument> {
  const data = await readJson<DeckProjectResponse>(
    await fetch(`/api/v1/decks/${deck.deck_id}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        ...editorTokenHeader(),
      },
      body: JSON.stringify({ deck }),
    })
  );
  return deckDocumentSchema.parse(data.deck_json);
}

export function deckPptxExportUrl(deckId: string, templateId = "client_cvc_master"): string {
  const params = new URLSearchParams({ template_id: templateId });
  return `/api/v1/decks/${encodeURIComponent(deckId)}/export/pptx?${params.toString()}`;
}

export function deckHtmlPreviewUrl(deckId: string): string {
  return `/api/v1/decks/${encodeURIComponent(deckId)}/preview/html`;
}

export async function exportDeckPptx(deckId: string, templateId = "client_cvc_master"): Promise<Blob> {
  const response = await fetch(deckPptxExportUrl(deckId, templateId));
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  return response.blob();
}
