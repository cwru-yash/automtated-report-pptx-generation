import logging
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
                    import os

                    if os.path.isfile(image_path):
                        left, top, width, height = (
                            shape.left,
                            shape.top,
                            shape.width,
                            shape.height,
                        )
                        slide.shapes.add_picture(image_path, left, top, width, height)
                        logger.debug("Injected image into shape '%s'", shape.name)
                    else:
                        logger.warning(
                            "Image not found for shape '%s': %s",
                            shape.name,
                            image_path,
                        )

        prs.save(output_path)
        logger.info("PPT rendered to %s", output_path)
        return output_path


def render_ppt(
    bundle: AnalysisBundle,
    sections: Dict[str, str],
    template_id: str,
    output_path: str,
    images: Optional[Dict[str, str]] = None,
) -> str:
    return PPTRenderer().render(bundle, sections, template_id, output_path, images)
