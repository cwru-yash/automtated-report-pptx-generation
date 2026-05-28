import { create } from "zustand";

type GenerationStatus = "idle" | "loading" | "ready" | "error";

type GenerationStore = {
  generationStatus: GenerationStatus;
  activeStep: string;
  errors: string[];
  outline: Record<string, unknown> | null;
  setLoading: (step: string) => void;
  setReady: (outline?: Record<string, unknown>) => void;
  setError: (message: string) => void;
};

export const useGenerationStore = create<GenerationStore>()((set) => ({
  generationStatus: "idle",
  activeStep: "",
  errors: [],
  outline: null,
  setLoading: (activeStep) =>
    set({ generationStatus: "loading", activeStep, errors: [] }),
  setReady: (outline) =>
    set({ generationStatus: "ready", activeStep: "Deck ready", outline: outline ?? null }),
  setError: (message) =>
    set((state) => ({
      generationStatus: "error",
      activeStep: "Generation failed",
      errors: [...state.errors, message],
    })),
}));
