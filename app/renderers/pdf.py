import logging
import os
from typing import Dict, Optional

from app.bundle.schema import AnalysisBundle
from app.renderers.html import HTMLRenderer, HTMLRenderMode

logger = logging.getLogger(__name__)

homebrew_lib = "/opt/homebrew/lib"
if os.path.isdir(homebrew_lib):
    current_dyld_path = os.environ.get("DYLD_LIBRARY_PATH", "")
    if homebrew_lib not in current_dyld_path.split(":"):
        os.environ["DYLD_LIBRARY_PATH"] = (
            f"{homebrew_lib}:{current_dyld_path}" if current_dyld_path else homebrew_lib
        )

try:
    import weasyprint
    _WEASYPRINT_AVAILABLE = True
    _WEASYPRINT_IMPORT_ERROR = None
except (ImportError, OSError) as exc:
    _WEASYPRINT_AVAILABLE = False
    _WEASYPRINT_IMPORT_ERROR = exc


class PDFRenderer:
    def __init__(self, html_renderer: HTMLRenderer):
        self._html_renderer = html_renderer

    def render(
        self,
        bundle: AnalysisBundle,
        sections: Dict[str, str],
        language: str = "en-US",
        output_path: Optional[str] = None,
    ) -> bytes:
        """
        Renders narrative sections to PDF via WeasyPrint (using minimal HTML mode).

        Args:
            bundle: The canonical AnalysisBundle.
            sections: Dict of section key → text.
            language: Locale language code.
            output_path: If provided, writes PDF bytes to this path.

        Returns:
            Raw PDF bytes.
        """
        if not _WEASYPRINT_AVAILABLE:
            raise ImportError(
                "WeasyPrint is required for PDF rendering but is not installed or its system "
                "dependencies are missing.\n"
                "Install system deps with: brew install pango cairo\n"
                "Then: pip install weasyprint\n"
                f"Original import error: {_WEASYPRINT_IMPORT_ERROR}"
            )

        html_string = self._html_renderer.render(
            bundle, sections, language=language, mode=HTMLRenderMode.minimal
        )

        pdf_bytes = weasyprint.HTML(string=html_string).write_pdf()

        if output_path:
            with open(output_path, "wb") as f:
                f.write(pdf_bytes)
            logger.info(f"PDF written to {output_path}")

        return pdf_bytes


def render_pdf(
    bundle: AnalysisBundle,
    sections: Dict[str, str],
    html_renderer: HTMLRenderer,
    language: str = "en-US",
    output_path: Optional[str] = None,
) -> bytes:
    """Convenience function: instantiates PDFRenderer and calls render()."""
    return PDFRenderer(html_renderer).render(bundle, sections, language, output_path)
