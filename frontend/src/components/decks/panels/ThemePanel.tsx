import { useDeckStore } from "../../../stores/useDeckStore";

const accentOptions = ["#c8a45d", "#2f80ed", "#1f9d7a", "#d85050"];

export function ThemePanel() {
  const deck = useDeckStore((state) => state.currentDeck);
  const setTheme = useDeckStore((state) => state.setTheme);

  if (!deck) {
    return null;
  }

  return (
    <aside className="properties-panel" aria-label="Theme and properties">
      <h2>Theme</h2>
      <label>
        Deck title
        <input
          value={deck.title}
          readOnly
          aria-label="Deck title"
        />
      </label>
      <div className="swatches" aria-label="Accent color">
        {accentOptions.map((accent) => (
          <button
            type="button"
            key={accent}
            className={deck.theme.accent_color === accent ? "active" : ""}
            style={{ background: accent }}
            onClick={() => setTheme({ ...deck.theme, accent_color: accent })}
            aria-label={`Set accent ${accent}`}
          />
        ))}
      </div>
      <p className="panel-note">
        Drafts save locally first, then debounce to the FastAPI deck endpoint.
      </p>
    </aside>
  );
}
