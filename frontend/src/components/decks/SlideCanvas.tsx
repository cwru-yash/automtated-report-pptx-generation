import type { DeckSlideDocument } from "../../lib/decks/deck-schema";
import { useDeckStore } from "../../stores/useDeckStore";
import { ContentRenderer } from "./ContentRenderer";

export function SlideCanvas({ slide }: { slide: DeckSlideDocument | undefined }) {
  const selectBlock = useDeckStore((state) => state.selectBlock);

  if (!slide) {
    return <main className="slide-canvas empty">Choose a slide to edit.</main>;
  }

  return (
    <main className="slide-canvas" onClick={() => selectBlock(null)}>
      <section className={`slide-sheet ${slide.type}`} aria-label={`Editing slide ${slide.title}`}>
        {slide.content.map((block) => (
          <ContentRenderer block={block} key={block.id} />
        ))}
      </section>
    </main>
  );
}
