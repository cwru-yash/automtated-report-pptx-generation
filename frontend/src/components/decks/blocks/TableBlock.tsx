import type { ContentBlock } from "../../../lib/decks/deck-schema";

type TableBlock = Extract<ContentBlock, { type: "table" }>;

export function TableBlock({ block }: { block: TableBlock }) {
  return (
    <table className="deck-table" aria-label="Evidence table">
      <thead>
        <tr>
          {block.headers.map((header) => (
            <th key={header}>{header}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {block.rows.map((row, rowIndex) => (
          <tr key={`row-${rowIndex}`}>
            {row.map((cell, cellIndex) => (
              <td key={`cell-${rowIndex}-${cellIndex}`}>{cell}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
