import logging
import os
from typing import Dict, Optional

from app.bundle.schema import AnalysisBundle
from app.templates.registry import TemplateType, registry

logger = logging.getLogger(__name__)


class PPTRenderer:
    def render(
        self,
        bundle: AnalysisBundle,
        sections: Dict[str, str],
        template_id: str,
        output_path: str,
        images: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Renders a .pptx file by injecting narrative sections into named shape placeholders.
        """
        try:
            from pptx import Presentation
        except ImportError:
            raise ImportError(
                "python-pptx is required for PPT rendering. "
                "Install with: pip install python-pptx"
            )

        images = images or {}
        spec = registry.get_template(template_id)

        if spec.template_type != TemplateType.ppt:
            raise ValueError(
                f"Template '{template_id}' is not a PPT template (type={spec.template_type})"
            )

        prs = Presentation(spec.file_path)
        inserted_images: set[str] = set()

        for slide in prs.slides:
            for shape in slide.shapes:
                if shape.name in sections and shape.has_text_frame:
                    tf = shape.text_frame
                    if tf.paragraphs and tf.paragraphs[0].runs:
                        tf.paragraphs[0].runs[0].text = sections[shape.name]
                    else:
                        tf.clear()
                        tf.paragraphs[0].text = sections[shape.name]
                    logger.debug("Injected text into shape '%s'", shape.name)

                if shape.name in images:
                    image_path = images[shape.name]

                    if os.path.isfile(image_path):
                        left, top, width, height = (
                            shape.left,
                            shape.top,
                            shape.width,
                            shape.height,
                        )
                        slide.shapes.add_picture(image_path, left, top, width, height)
                        inserted_images.add(shape.name)
                        logger.debug("Injected image into shape '%s'", shape.name)
                    else:
                        logger.warning(
                            "Image not found for shape '%s': %s",
                            shape.name,
                            image_path,
                        )

        missing_image_slots = {
            image_key: image_path
            for image_key, image_path in images.items()
            if image_key not in inserted_images
        }
        if missing_image_slots:
            self._append_chart_slides(prs, missing_image_slots)

        prs.save(output_path)
        logger.info("PPT rendered to %s", output_path)
        return output_path

    def _append_chart_slides(self, prs, images: Dict[str, str]) -> None:
        from pptx.util import Inches, Pt

        blank_layout = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[-1]
        titles = {
            "chart_1": "Industry Average Curve",
            "chart_6": "Achilles Heel",
            "chart_7": "Best of Best",
        }

        for image_key, image_path in sorted(images.items()):
            if not os.path.isfile(image_path):
                logger.warning("Chart image not found for appended slide: %s", image_path)
                continue

            slide = prs.slides.add_slide(blank_layout)
            title_box = slide.shapes.add_textbox(Inches(0.7), Inches(0.35), Inches(12.0), Inches(0.45))
            title_frame = title_box.text_frame
            title_frame.clear()
            run = title_frame.paragraphs[0].add_run()
            run.text = titles.get(image_key, image_key.replace("_", " ").title())
            run.font.size = Pt(24)

            slide.shapes.add_picture(
                image_path,
                Inches(0.7),
                Inches(1.0),
                width=Inches(12.0),
                height=Inches(5.9),
            )
            logger.debug("Appended chart slide for '%s'", image_key)


def render_ppt(
    bundle: AnalysisBundle,
    sections: Dict[str, str],
    template_id: str,
    output_path: str,
    images: Optional[Dict[str, str]] = None,
) -> str:
    return PPTRenderer().render(bundle, sections, template_id, output_path, images)
