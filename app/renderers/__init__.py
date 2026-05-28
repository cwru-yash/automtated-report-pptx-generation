__all__ = [
    "PPTRenderer", "render_ppt", "render_deck_document_ppt",
    "HTMLRenderer", "HTMLRenderMode", "render_html",
    "PDFRenderer", "render_pdf",
]


def __getattr__(name):
    if name in {"PPTRenderer", "render_ppt", "render_deck_document_ppt"}:
        from app.renderers.ppt import PPTRenderer, render_deck_document_ppt, render_ppt
        return {
            "PPTRenderer": PPTRenderer,
            "render_ppt": render_ppt,
            "render_deck_document_ppt": render_deck_document_ppt,
        }[name]
    if name in {"HTMLRenderer", "HTMLRenderMode", "render_html"}:
        from app.renderers.html import HTMLRenderer, HTMLRenderMode, render_html
        return {
            "HTMLRenderer": HTMLRenderer,
            "HTMLRenderMode": HTMLRenderMode,
            "render_html": render_html,
        }[name]
    if name in {"PDFRenderer", "render_pdf"}:
        from app.renderers.pdf import PDFRenderer, render_pdf
        return {"PDFRenderer": PDFRenderer, "render_pdf": render_pdf}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
