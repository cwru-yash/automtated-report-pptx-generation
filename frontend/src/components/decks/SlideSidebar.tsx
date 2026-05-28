import type { DeckSlideDocument } from "../../lib/decks/deck-schema";
import { useDeckStore } from "../../stores/useDeckStore";

export function SlideSidebar({ slides }: { slides: DeckSlideDocument[] }) {
  const selectedSlideId = useDeckStore((state) => state.selectedSlideId);
  const selectSlide = useDeckStore((state) => state.selectSlide);
  const reorderSlides = useDeckStore((state) => state.reorderSlides);

  return (
    <aside className="slide-sidebar" aria-label="Slide thumbnails">
      {slides.map((slide, index) => (
        <article
          key={slide.id}
          className={`slide-thumb ${selectedSlideId === slide.id ? "active" : ""}`}
          onClick={() => selectSlide(slide.id)}
        >
          <span>{index + 1}</span>
          <strong>{slide.title}</strong>
          <div className="thumb-actions">
            <button
              type="button"
              disabled={index === 0}
              onClick={(event) => {
                event.stopPropagation();
                reorderSlides(index, index - 1);
              }}
              aria-label="Move slide up"
            >
              ↑
            </button>
            <button
              type="button"
              disabled={index === slides.length - 1}
              onClick={(event) => {
                event.stopPropagation();
                reorderSlides(index, index + 1);
              }}
              aria-label="Move slide down"
            >
              ↓
            </button>
          </div>
        </article>
      ))}
    </aside>
  );
}
