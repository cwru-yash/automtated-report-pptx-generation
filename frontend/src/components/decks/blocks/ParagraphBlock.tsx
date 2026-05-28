import type { ContentBlock } from "../../../lib/decks/deck-schema";
import { useDeckStore } from "../../../stores/useDeckStore";

type ParagraphLikeBlock = Extract<ContentBlock, { type: "paragraph" | "quote" | "callout" | "footnote" | "source_note" }>;

export function ParagraphBlock({ block }: { block: ParagraphLikeBlock }) {
  const updateBlock = useDeckStore((state) => state.updateBlock);

  return (
    <textarea
      className={`deck-text ${block.type}`}
      value={block.text}
      onChange={(event) => updateBlock(block.id, { text: event.target.value })}
      aria-label={`${block.type} text`}
      rows={block.type === "paragraph" ? 4 : 2}
    />
  );
}
