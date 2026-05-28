import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

type GenerationMode = "from_wave" | "from_prompt";

type PromptStore = {
  latestUserPrompt: string;
  reportSourceId: string;
  generationMode: GenerationMode;
  setPrompt: (prompt: string) => void;
  setReportSourceId: (sourceId: string) => void;
  setGenerationMode: (mode: GenerationMode) => void;
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

export const usePromptStore = create<PromptStore>()(
  persist(
    (set) => ({
      latestUserPrompt: "",
      reportSourceId: "",
      generationMode: "from_wave",
      setPrompt: (latestUserPrompt) => set({ latestUserPrompt }),
      setReportSourceId: (reportSourceId) => set({ reportSourceId }),
      setGenerationMode: (generationMode) => set({ generationMode }),
    }),
    {
      name: "report-to-deck-prompt-v1",
      storage: createJSONStorage(safeJsonStorage),
      partialize: (state) => ({
        latestUserPrompt: state.latestUserPrompt,
        reportSourceId: state.reportSourceId,
        generationMode: state.generationMode,
      }),
    }
  )
);
