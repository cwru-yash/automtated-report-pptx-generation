import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { ContentBlock, DeckDocument, DeckSlideDocument, DeckTheme } from "../lib/decks/deck-schema";

type SaveState = "saved" | "saving" | "dirty" | "error";

type DeckStore = {
  currentDeck: DeckDocument | null;
  selectedSlideId: string | null;
  selectedBlockId: string | null;
  saveState: SaveState;
  errorMessage: string;
  setDeck: (deck: DeckDocument) => void;
  selectSlide: (slideId: string) => void;
  selectBlock: (blockId: string | null) => void;
  updateBlock: (blockId: string, patch: Partial<ContentBlock>) => void;
  reorderSlides: (fromIndex: number, toIndex: number) => void;
  addBlock: (slideId: string, block: ContentBlock) => void;
  deleteBlock: (blockId: string) => void;
  setTheme: (theme: DeckTheme) => void;
  setSaveState: (saveState: SaveState, errorMessage?: string) => void;
};

function safeJsonStorage() {
  const memory = new Map<string, string>();
  const fallback = {
    getItem: (name: string) => memory.get(name) ?? null,
    setItem: (name: string, value: string) => {
      memory.set(name, value);
    },
    removeItem: (name: string) => {
      memory.delete(name);
    },
  };

  if (typeof window === "undefined") {
    return fallback;
  }
  try {
    if (
      typeof window.localStorage.getItem === "function" &&
      typeof window.localStorage.setItem === "function" &&
      typeof window.localStorage.removeItem === "function"
    ) {
      return window.localStorage;
    }
  } catch {
    return fallback;
  }
  return fallback;
}

function updateBlockList(
  blocks: ContentBlock[],
  blockId: string,
  patch: Partial<ContentBlock>
): [ContentBlock[], boolean] {
  let changed = false;
  const nextBlocks = blocks.map((block) => {
    if (block.id === blockId) {
      changed = true;
      return { ...block, ...patch } as ContentBlock;
    }
    if ("columns" in block) {
      const nextColumns = block.columns.map((column) => {
        const [content, nestedChanged] = updateBlockList(column.content, blockId, patch);
        changed = changed || nestedChanged;
        return { ...column, content };
      }) as typeof block.columns;
      return { ...block, columns: nextColumns } as ContentBlock;
    }
    return block;
  });
  return [nextBlocks, changed];
}

function deleteBlockList(blocks: ContentBlock[], blockId: string): [ContentBlock[], boolean] {
  let changed = false;
  const filtered = blocks.filter((block) => {
    if (block.id === blockId) {
      changed = true;
      return false;
    }
    return true;
  });
  const nextBlocks = filtered.map((block) => {
    if ("columns" in block) {
      const nextColumns = block.columns.map((column) => {
        const [content, nestedChanged] = deleteBlockList(column.content, blockId);
        changed = changed || nestedChanged;
        return { ...column, content };
      }) as typeof block.columns;
      return { ...block, columns: nextColumns } as ContentBlock;
    }
    return block;
  });
  return [nextBlocks, changed];
}

function markDirty(deck: DeckDocument | null): DeckDocument | null {
  if (!deck) {
    return deck;
  }
  return {
    ...deck,
    metadata: {
      ...deck.metadata,
      edited_at: new Date().toISOString(),
    },
  };
}

export const useDeckStore = create<DeckStore>()(
  persist(
    (set) => ({
      currentDeck: null,
      selectedSlideId: null,
      selectedBlockId: null,
      saveState: "saved",
      errorMessage: "",
      setDeck: (deck) =>
        set({
          currentDeck: deck,
          selectedSlideId: deck.slides[0]?.id ?? null,
          selectedBlockId: null,
          saveState: "saved",
          errorMessage: "",
        }),
      selectSlide: (slideId) => set({ selectedSlideId: slideId, selectedBlockId: null }),
      selectBlock: (blockId) => set({ selectedBlockId: blockId }),
      updateBlock: (blockId, patch) =>
        set((state) => {
          if (!state.currentDeck) {
            return state;
          }
          const slides = state.currentDeck.slides.map((slide) => {
            const [content, changed] = updateBlockList(slide.content, blockId, patch);
            return changed ? { ...slide, content } : slide;
          });
          return {
            currentDeck: markDirty({ ...state.currentDeck, slides }),
            saveState: "dirty",
            errorMessage: "",
          };
        }),
      reorderSlides: (fromIndex, toIndex) =>
        set((state) => {
          if (!state.currentDeck) {
            return state;
          }
          const slides = [...state.currentDeck.slides];
          const [moved] = slides.splice(fromIndex, 1);
          if (!moved) {
            return state;
          }
          slides.splice(toIndex, 0, moved);
          return {
            currentDeck: markDirty({ ...state.currentDeck, slides }),
            saveState: "dirty",
          };
        }),
      addBlock: (slideId, block) =>
        set((state) => {
          if (!state.currentDeck) {
            return state;
          }
          const slides = state.currentDeck.slides.map((slide): DeckSlideDocument => {
            if (slide.id !== slideId) {
              return slide;
            }
            return { ...slide, content: [...slide.content, block] };
          });
          return {
            currentDeck: markDirty({ ...state.currentDeck, slides }),
            selectedBlockId: block.id,
            saveState: "dirty",
          };
        }),
      deleteBlock: (blockId) =>
        set((state) => {
          if (!state.currentDeck) {
            return state;
          }
          const slides = state.currentDeck.slides.map((slide) => {
            const [content, changed] = deleteBlockList(slide.content, blockId);
            return changed ? { ...slide, content } : slide;
          });
          return {
            currentDeck: markDirty({ ...state.currentDeck, slides }),
            selectedBlockId: state.selectedBlockId === blockId ? null : state.selectedBlockId,
            saveState: "dirty",
          };
        }),
      setTheme: (theme) =>
        set((state) => {
          if (!state.currentDeck) {
            return state;
          }
          return {
            currentDeck: markDirty({ ...state.currentDeck, theme }),
            saveState: "dirty",
          };
        }),
      setSaveState: (saveState, errorMessage = "") => set({ saveState, errorMessage }),
    }),
    {
      name: "report-to-deck-draft-v1",
      storage: createJSONStorage(safeJsonStorage),
      partialize: (state) => ({
        currentDeck: state.currentDeck,
        selectedSlideId: state.selectedSlideId,
      }),
    }
  )
);
