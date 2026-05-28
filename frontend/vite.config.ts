import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/decks/editor/",
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
  },
});
