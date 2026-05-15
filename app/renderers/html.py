import json
import logging
import os
from enum import Enum
from typing import Dict

import jinja2

from app.bundle.schema import AnalysisBundle

logger = logging.getLogger(__name__)

SECTION_ORDER = ["exec_summary", "methodology", "brand_health", "weak_links", "takeaways"]


class HTMLRenderMode(str, Enum):
    branded = "branded"
    minimal = "minimal"


class HTMLRenderer:
    def __init__(self, templates_dir: str, locales_dir: str):
        html_templates_path = os.path.join(templates_dir, "html")
        if not os.path.isdir(html_templates_path):
            html_templates_path = os.path.join(
                os.path.dirname(__file__), "..", "templates", "html"
            )
        self._env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(html_templates_path),
            autoescape=jinja2.select_autoescape(["html"]),
        )
        self._locales_dir = locales_dir

    def _load_locale(self, language: str) -> dict:
        path = os.path.join(self._locales_dir, f"{language}.json")
        if not os.path.isfile(path):
            logger.warning(
                "Locale file not found for '%s': %s - falling back to en-US",
                language,
                path,
            )
            path = os.path.join(self._locales_dir, "en-US.json")
        if not os.path.isfile(path):
            logger.warning("en-US locale file also missing - using empty labels")
            return {}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def render(
        self,
        bundle: AnalysisBundle,
        sections: Dict[str, str],
        language: str = "en-US",
        mode: HTMLRenderMode = HTMLRenderMode.branded,
    ) -> str:
        labels = self._load_locale(language)
        template_name = (
            "branded.html.j2" if mode == HTMLRenderMode.branded else "minimal.html.j2"
        )
        template = self._env.get_template(template_name)
        return template.render(
            bundle=bundle,
            sections=sections,
            labels=labels,
            language=language,
            section_order=SECTION_ORDER,
        )


def render_html(
    bundle: AnalysisBundle,
    sections: Dict[str, str],
    templates_dir: str,
    locales_dir: str,
    language: str = "en-US",
    mode: HTMLRenderMode = HTMLRenderMode.branded,
) -> str:
    return HTMLRenderer(templates_dir, locales_dir).render(
        bundle,
        sections,
        language,
        mode,
    )
