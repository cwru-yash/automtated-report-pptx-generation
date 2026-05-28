import type { ContentBlock } from "../../../lib/decks/deck-schema";
import { useDeckStore } from "../../../stores/useDeckStore";

type MetricCardBlock = Extract<ContentBlock, { type: "metric_card" }>;

export function MetricCardBlock({ block }: { block: MetricCardBlock }) {
  const updateBlock = useDeckStore((state) => state.updateBlock);

  return (
    <div className="metric-card">
      <input
        className="metric-label"
        value={block.label}
        onChange={(event) => updateBlock(block.id, { label: event.target.value })}
        aria-label="Metric label"
      />
      <input
        className="metric-value"
        value={String(block.value)}
        onChange={(event) => updateBlock(block.id, { value: event.target.value })}
        aria-label="Metric value"
      />
      <input
        className="metric-helper"
        value={block.helper ?? ""}
        onChange={(event) => updateBlock(block.id, { helper: event.target.value })}
        aria-label="Metric helper"
      />
    </div>
  );
}
