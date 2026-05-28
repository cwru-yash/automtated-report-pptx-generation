from __future__ import annotations

from html import escape

from app.deck.layout_schema import ContentBlock, DeckDocument


def render_deck_document_html(deck: DeckDocument) -> str:
    """Render a validated DeckDocument as simple escaped semantic HTML."""
    title = escape(deck.title)
    slides = "\n".join(_render_slide(index, slide) for index, slide in enumerate(deck.slides, start=1))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; line-height: 1.5; margin: 2rem; color: #17202a; }}
    main {{ display: grid; gap: 1.5rem; }}
    section {{ border: 1px solid #d8dde4; border-radius: 8px; padding: 1rem; }}
    .columns {{ display: flex; gap: 1rem; margin: 1rem 0; }}
    .column {{ flex: 1; border-left: 3px solid #d8dde4; padding-left: 0.75rem; }}
    .metric-card, .placeholder, .text-block {{ border: 1px solid #d8dde4; border-radius: 6px; padding: 0.75rem; margin: 0.75rem 0; }}
    table {{ border-collapse: collapse; width: 100%; margin: 0.75rem 0; }}
    th, td {{ border: 1px solid #d8dde4; padding: 0.45rem; text-align: left; }}
    blockquote {{ border-left: 3px solid #c8a45d; margin: 0.75rem 0; padding-left: 0.75rem; }}
  </style>
</head>
<body>
  <main>
    <h1>{title}</h1>
    {slides}
  </main>
</body>
</html>"""


def _render_slide(index: int, slide) -> str:
    content = "\n".join(_render_block(block) for block in slide.content)
    return f"""<section data-slide-id="{escape(slide.id)}">
  <h2>Slide {index}: {escape(slide.title)}</h2>
  {content}
</section>"""


def _render_block(block: ContentBlock) -> str:
    if block.type == "heading":
        level = min(max(block.level or 2, 1), 3)
        return f"<h{level}>{escape(block.text or '')}</h{level}>"
    if block.type == "paragraph":
        return f"<p>{escape(block.text or '')}</p>"
    if block.type == "bullet_list":
        return f"<ul>{''.join(f'<li>{escape(item)}</li>' for item in block.items)}</ul>"
    if block.type == "ordered_list":
        return f"<ol>{''.join(f'<li>{escape(item)}</li>' for item in block.items)}</ol>"
    if block.type == "metric_card":
        label = escape(block.label or "")
        value = escape(str(block.value))
        helper = f"<small>{escape(block.helper)}</small>" if block.helper else ""
        return f'<div class="metric-card"><strong>{label}</strong><div>{value}</div>{helper}</div>'
    if block.type == "table":
        headers = "".join(f"<th>{escape(header)}</th>" for header in block.headers)
        rows = "".join(
            "<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in row) + "</tr>"
            for row in block.rows
        )
        return f"<table><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>"
    if block.type == "chart_placeholder":
        chart_title = f" — {escape(block.title)}" if block.title else ""
        return f'<div class="placeholder"><strong>Chart placeholder:</strong> {escape(block.chart_ref or "")}{chart_title}</div>'
    if block.type == "image":
        image_label = block.alt or block.src or ""
        return f'<div class="placeholder"><strong>Image placeholder:</strong> {escape(image_label)}</div>'
    if block.type in {"source_note", "footnote", "callout"}:
        label = block.type.replace("_", " ").title()
        return f'<aside class="text-block {escape(block.type)}"><strong>{label}:</strong> {escape(block.text or "")}</aside>'
    if block.type == "quote":
        return f"<blockquote>{escape(block.text or '')}</blockquote>"
    if block.type in {"two_column", "three_column"}:
        columns = "".join(
            f'<div class="column" style="flex-basis:{column.width}%;">'
            + "".join(_render_block(child) for child in column.content)
            + "</div>"
            for column in block.columns
        )
        return f'<div class="columns {escape(block.type)}">{columns}</div>'
    if block.type == "divider":
        return "<hr>"
    return f'<div class="placeholder">Unsupported block type: {escape(str(block.type))}</div>'
