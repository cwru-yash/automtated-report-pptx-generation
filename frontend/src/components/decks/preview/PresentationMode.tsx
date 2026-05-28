import type { DeckDocument } from "../../../lib/decks/deck-schema";
import { ContentRenderer } from "../ContentRenderer";

export function PresentationMode({
  deck,
  onClose,
}: {
  deck: DeckDocument;
  onClose: () => void;
}) {
  return (
    <div className="presentation-mode">
      <button className="close-preview" type="button" onClick={onClose}>
        Close preview
      </button>
      {deck.slides.map((slide) => (
        <section className={`preview-slide ${slide.type}`} key={slide.id}>
          {slide.content.map((block) => (
            <ContentRenderer block={block} key={block.id} />
          ))}
        </section>
      ))}
    </div>
  );
}
