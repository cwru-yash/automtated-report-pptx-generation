from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import FastAPI
import logging
from pydantic import BaseModel, Field

from app.config import settings
from app.templates.registry import init_registry, registry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReportJobRequest(BaseModel):
    wave_id: str = Field(..., description="Completed Decomposer wave ID")
    language: str = Field(default="en-US", description="Locale for report labels and narrative")
    template_id: Optional[str] = Field(
        default="demo_master",
        description="Registered PPT template ID. Use null to skip PPT rendering.",
    )
    use_llm: bool = Field(default=True, description="Use LLM-backed LangGraph narrative nodes")
    require_llm: bool = Field(default=False, description="Fail sections instead of using fallback text")
    include_pdf: bool = Field(default=True, description="Render PDF artifact when WeasyPrint is available")
    output_dir: str = Field(default="artifacts", description="Local output directory for demo artifacts")


class ReportJobResponse(BaseModel):
    job_id: str
    status: str
    bundle: Dict[str, Any]
    sections: Dict[str, str]
    ppt_sections: Dict[str, str] = Field(default_factory=dict)
    llm_metadata: Dict[str, Any] = Field(default_factory=dict)
    artifacts: Dict[str, str]
    warnings: list[str] = Field(default_factory=list)


def ensure_template_registry_loaded() -> None:
    if not registry.list_templates():
        init_registry(settings.TEMPLATES_DIR)


def prewarm_demo_dependencies(app: FastAPI) -> None:
    """
    Load the demo generation path during startup so the first recorded job call
    does not pay import and template-cache costs on camera.
    """
    try:
        from app.bundle.assembler import BundleAssembler
        from app.bundle.schema import AnalysisBundle
        from app.narrative.graph import run_narrative_engine_async
        from app.renderers.html import HTMLRenderer
        from app.renderers.ppt import render_ppt

        app.state.bundle_assembler_cls = BundleAssembler
        app.state.run_narrative_engine_async = run_narrative_engine_async
        app.state.render_ppt = render_ppt
        app.state.html_renderer = HTMLRenderer(settings.TEMPLATES_DIR, settings.LOCALES_DIR)

        bundle = AnalysisBundle(
            wave_id="startup-prewarm",
            language="en-US",
            metrics={"nps": 0.0, "brand_awareness": 0.0, "cvc_score": 0.0},
            analysis_results={},
        )
        sections = {
            "exec_summary": "Prewarm",
            "methodology": "Prewarm",
            "brand_health": "Prewarm",
            "weak_links": "Prewarm",
            "takeaways": "Prewarm",
        }
        app.state.html_renderer.render(bundle, sections, language="en-US")

        try:
            from pptx import Presentation

            template = registry.get_template("demo_master")
            Presentation(template.file_path)
        except Exception as exc:
            logger.warning("PPT prewarm skipped: %s", exc)
    except Exception as exc:
        logger.warning("Demo dependency prewarm skipped: %s", exc)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up... Settings loaded securely.")
    init_registry(settings.TEMPLATES_DIR)
    prewarm_demo_dependencies(app)
    yield
    logger.info("Application shutting down...")

app = FastAPI(title="Automated Report Platform", lifespan=lifespan)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "automated-report-platform"}

@app.get("/api/v1/templates")
def list_templates():
    ensure_template_registry_loaded()
    return {"templates": [t.model_dump() for t in registry.list_templates()]}


@app.get("/api/v1/templates/{template_id}/inspect")
def inspect_template(template_id: str):
    ensure_template_registry_loaded()
    spec = registry.get_template(template_id)
    if spec.template_type.value != "ppt":
        return {"template": spec.model_dump(), "slides": []}

    from pptx import Presentation

    prs = Presentation(spec.file_path)
    required = {placeholder.name for placeholder in spec.placeholders}
    seen = set()
    slides = []

    for slide_number, slide in enumerate(prs.slides, start=1):
        shapes = []
        for shape in slide.shapes:
            text = ""
            if getattr(shape, "has_text_frame", False):
                text = shape.text.strip().replace("\n", " ")
            seen.add(shape.name)
            shapes.append(
                {
                    "name": shape.name,
                    "type": str(shape.shape_type),
                    "has_text_frame": bool(getattr(shape, "has_text_frame", False)),
                    "text_sample": text[:100],
                }
            )
        slides.append({"slide_number": slide_number, "shapes": shapes})

    return {
        "template": spec.model_dump(),
        "required_placeholders": sorted(required),
        "missing_placeholders": sorted(required - seen),
        "slides": slides,
    }


@app.post("/api/v1/jobs", response_model=ReportJobResponse)
async def create_report_job(request: ReportJobRequest):
    """
    Demo-ready synchronous job path.

    The production design can move this behind the Postgres queue, but for a POC
    recording it proves the full Bundle -> Narrative -> HTML/PPT flow in one call.
    """
    ensure_template_registry_loaded()

    BundleAssembler = getattr(app.state, "bundle_assembler_cls", None)
    run_narrative_engine_async = getattr(app.state, "run_narrative_engine_async", None)
    render_ppt = getattr(app.state, "render_ppt", None)
    html_renderer = getattr(app.state, "html_renderer", None)

    if not all([BundleAssembler, run_narrative_engine_async, render_ppt, html_renderer]):
        from app.bundle.assembler import BundleAssembler
        from app.narrative.graph import run_narrative_engine_async
        from app.renderers.html import HTMLRenderer
        from app.renderers.ppt import render_ppt

        html_renderer = HTMLRenderer(settings.TEMPLATES_DIR, settings.LOCALES_DIR)

    job_id = str(uuid4())
    output_dir = Path(request.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    bundle = await BundleAssembler().build_bundle(request.wave_id, request.language)
    narrative = await run_narrative_engine_async(
        bundle,
        use_llm=request.use_llm,
        require_llm=request.require_llm,
    )
    sections = narrative.get("sections", {})
    ppt_sections = narrative.get("ppt_sections", {})
    llm_metadata = narrative.get("llm_metadata", {})
    warnings = [str(error) for error in narrative.get("errors", [])]
    status = "failed" if request.require_llm and warnings else "completed"

    artifacts: Dict[str, str] = {}

    if status == "failed":
        return ReportJobResponse(
            job_id=job_id,
            status=status,
            bundle=bundle.model_dump(),
            sections=sections,
            ppt_sections=ppt_sections,
            llm_metadata=llm_metadata,
            artifacts=artifacts,
            warnings=warnings,
        )

    html = html_renderer.render(bundle, sections, language=request.language)
    html_path = output_dir / f"{job_id}.html"
    html_path.write_text(html, encoding="utf-8")
    artifacts["html"] = str(html_path)

    if request.template_id:
        try:
            ppt_path = output_dir / f"{job_id}.pptx"
            render_ppt(bundle, ppt_sections or sections, request.template_id, str(ppt_path))
            artifacts["pptx"] = str(ppt_path)
        except Exception as exc:
            logger.exception("PPT rendering failed")
            warnings.append(f"PPT rendering skipped: {exc}")

    if request.include_pdf:
        try:
            from app.renderers.pdf import render_pdf

            pdf_path = output_dir / f"{job_id}.pdf"
            render_pdf(
                bundle=bundle,
                sections=sections,
                html_renderer=html_renderer,
                language=request.language,
                output_path=str(pdf_path),
            )
            artifacts["pdf"] = str(pdf_path)
        except Exception as exc:
            logger.exception("PDF rendering failed")
            warnings.append(f"PDF rendering skipped: {exc}")

    return ReportJobResponse(
        job_id=job_id,
        status=status,
        bundle=bundle.model_dump(),
        sections=sections,
        ppt_sections=ppt_sections,
        llm_metadata=llm_metadata,
        artifacts=artifacts,
        warnings=warnings,
    )
