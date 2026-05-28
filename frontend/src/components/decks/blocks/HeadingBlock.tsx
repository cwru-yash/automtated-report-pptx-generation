import type { ContentBlock } from "../../../lib/decks/deck-schema";
import { useDeckStore } from "../../../stores/useDeckStore";

type HeadingBlock = Extract<ContentBlock, { type: "heading" }>;

export function HeadingBlock({ block }: { block: HeadingBlock }) {
  const updateBlock = useDeckStore((state) => state.updateBlock);
  const Tag = block.level === 1 ? "h1" : block.level === 2 ? "h2" : "h3";

  return (
    <Tag className={`deck-heading level-${block.level}`}>
      <textarea
        value={block.text}
        rows={block.level === 1 ? 2 : 1}
        onChange={(event) => updateBlock(block.id, { text: event.target.value })}
        aria-label="Heading text"
      />
    </Tag>
  );
}
