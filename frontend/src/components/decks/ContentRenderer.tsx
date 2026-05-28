import type { ContentBlock } from "../../lib/decks/deck-schema";
import { useDeckStore } from "../../stores/useDeckStore";
import { BulletListBlock } from "./blocks/BulletListBlock";
import { ChartPlaceholderBlock } from "./blocks/ChartPlaceholderBlock";
import { HeadingBlock } from "./blocks/HeadingBlock";
import { MetricCardBlock } from "./blocks/MetricCardBlock";
import { ParagraphBlock } from "./blocks/ParagraphBlock";
import { TableBlock } from "./blocks/TableBlock";

type UnsafeBlock = {
  id?: string;
  type?: string;
  [key: string]: unknown;
};

export function ContentRenderer({ block }: { block: ContentBlock | UnsafeBlock }) {
  const selectedBlockId = useDeckStore((state) => state.selectedBlockId);
  const selectBlock = useDeckStore((state) => state.selectBlock);
  const blockId = typeof block.id === "string" ? block.id : "unknown-block";
  const selected = selectedBlockId === blockId;

  return (
    <div
      className={`content-block ${selected ? "selected" : ""}`}
      onClick={(event) => {
        event.stopPropagation();
        selectBlock(blockId);
      }}
    >
      {renderKnownBlock(block)}
    </div>
  );
}

function renderKnownBlock(block: ContentBlock | UnsafeBlock) {
  switch (block.type) {
    case "heading":
      return <HeadingBlock block={block as Extract<ContentBlock, { type: "heading" }>} />;
    case "paragraph":
    case "quote":
    case "callout":
    case "footnote":
    case "source_note":
      return <ParagraphBlock block={block as Extract<ContentBlock, { type: "paragraph" | "quote" | "callout" | "footnote" | "source_note" }>} />;
    case "bullet_list":
    case "ordered_list":
      return <BulletListBlock block={block as Extract<ContentBlock, { type: "bullet_list" | "ordered_list" }>} />;
    case "metric_card":
      return <MetricCardBlock block={block as Extract<ContentBlock, { type: "metric_card" }>} />;
    case "chart_placeholder":
      return <ChartPlaceholderBlock block={block as Extract<ContentBlock, { type: "chart_placeholder" }>} />;
    case "two_column":
    case "three_column": {
      const columnBlock = block as Extract<ContentBlock, { type: "two_column" | "three_column" }>;
      return (
        <div className={`column-block ${columnBlock.type}`}>
          {columnBlock.columns.map((column, index) => (
            <div className="deck-column" style={{ flexBasis: `${column.width}%` }} key={`${columnBlock.id}-${index}`}>
              {column.content.map((child) => (
                <ContentRenderer block={child} key={child.id} />
              ))}
            </div>
          ))}
        </div>
      );
    }
    case "divider":
      return <hr className="deck-divider" />;
    case "table":
      return <TableBlock block={block as Extract<ContentBlock, { type: "table" }>} />;
    case "image":
      return <div className="safe-block">Image block: {(block as { src?: string }).src}</div>;
    default:
      return (
        <div className="safe-block" role="alert">
          Unsupported block type: {String(block.type || "missing")}
        </div>
      );
  }
}
