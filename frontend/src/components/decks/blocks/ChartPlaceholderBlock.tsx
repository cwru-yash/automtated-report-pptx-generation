import type { ContentBlock } from "../../../lib/decks/deck-schema";

type ChartPlaceholderBlock = Extract<ContentBlock, { type: "chart_placeholder" }>;

export function ChartPlaceholderBlock({ block }: { block: ChartPlaceholderBlock }) {
  return (
    <div className="chart-placeholder">
      <span>{block.chart_ref}</span>
      <strong>{block.title || "Chart placeholder"}</strong>
    </div>
  );
}
