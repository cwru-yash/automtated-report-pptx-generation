import type { ContentBlock } from "../../../lib/decks/deck-schema";
import { useDeckStore } from "../../../stores/useDeckStore";

type ListBlock = Extract<ContentBlock, { type: "bullet_list" | "ordered_list" }>;

export function BulletListBlock({ block }: { block: ListBlock }) {
  const updateBlock = useDeckStore((state) => state.updateBlock);

  return (
    <textarea
      className="deck-list-editor"
      value={block.items.join("\n")}
      onChange={(event) =>
        updateBlock(block.id, {
          items: event.target.value
            .split("\n")
            .map((item) => item.trim())
            .filter(Boolean),
        })
      }
      aria-label="List items"
      rows={Math.max(3, block.items.length)}
    />
  );
}
