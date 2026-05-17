import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import logging
from pydantic import BaseModel, Field

from app.config import settings
from app.observability import StructuredEventLogger, read_jsonl
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
    batch_id: Optional[str] = None
    status: str
    bundle: Dict[str, Any]
    sections: Dict[str, str]
    ppt_sections: Dict[str, str] = Field(default_factory=dict)
    llm_metadata: Dict[str, Any] = Field(default_factory=dict)
    artifacts: Dict[str, str]
    warnings: list[str] = Field(default_factory=list)
    logs_url: str


class BatchReportJobRequest(BaseModel):
    wave_id: str = Field(..., description="Completed Decomposer wave ID")
    languages: list[str] = Field(
        default_factory=lambda: ["en-US"],
        description="Locales to generate as independent child jobs.",
    )
    template_id: Optional[str] = Field(
        default="demo_master",
        description="Registered PPT template ID. Use null to skip PPT rendering.",
    )
    use_llm: bool = Field(default=True, description="Use LLM-backed LangGraph narrative nodes")
    require_llm: bool = Field(default=False, description="Fail sections instead of using fallback text")
    include_pdf: bool = Field(default=True, description="Render PDF artifact when WeasyPrint is available")
    output_dir: str = Field(default="artifacts", description="Local output directory for demo artifacts")


class BatchChildJobResponse(BaseModel):
    language: str
    job_id: str
    status: str
    artifacts: Dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    llm_metadata: Dict[str, Any] = Field(default_factory=dict)
    logs_url: str


class BatchReportJobResponse(BaseModel):
    batch_id: str
    status: str
    wave_id: str
    template_id: Optional[str]
    languages: list[str]
    children: list[BatchChildJobResponse]
    logs_url: str


def ensure_template_registry_loaded() -> None:
    if not registry.list_templates():
        init_registry(settings.TEMPLATES_DIR)


def dedupe_preserving_order(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def log_path(kind: str, identifier: str) -> Path:
    return Path(settings.LOGS_DIR) / kind / f"{identifier}.jsonl"


def get_demo_dependencies():
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

    return BundleAssembler, run_narrative_engine_async, render_ppt, html_renderer


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
STATIC_DIR = Path(__file__).parent / "static"
ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/artifacts", StaticFiles(directory=ARTIFACTS_DIR), name="artifacts")


@app.get("/", include_in_schema=False)
def report_console():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "automated-report-platform"}


@app.get("/api/v1/locales")
def list_locales():
    locales_dir = Path(settings.LOCALES_DIR)
    locales = []
    if locales_dir.is_dir():
        locales = sorted(path.stem for path in locales_dir.glob("*.json"))
    return {"locales": locales}


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


async def execute_report_job(
    request: ReportJobRequest,
    *,
    job_id: str | None = None,
    batch_id: str | None = None,
) -> ReportJobResponse:
    ensure_template_registry_loaded()
    BundleAssembler, run_narrative_engine_async, render_ppt, html_renderer = get_demo_dependencies()

    job_id = job_id or str(uuid4())
    output_dir = Path(request.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    event_log = StructuredEventLogger(
        settings.LOGS_DIR,
        batch_id=batch_id,
        job_id=job_id,
        context={
            "wave_id": request.wave_id,
            "language": request.language,
            "template_id": request.template_id,
        },
    )
    event_log.emit(
        "job.started",
        use_llm=request.use_llm,
        require_llm=request.require_llm,
        include_pdf=request.include_pdf,
    )

    try:
        bundle = await BundleAssembler().build_bundle(request.wave_id, request.language)
        event_log.emit(
            "bundle.assembled",
            metric_keys=sorted(bundle.metrics.keys()),
            analysis_keys=sorted(bundle.analysis_results.keys()),
        )

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
        event_log.emit(
            "narrative.completed",
            status=status,
            section_count=len(sections),
            llm_modes={
                key: value.get("mode")
                for key, value in llm_metadata.items()
            },
            warning_count=len(warnings),
        )

        artifacts: Dict[str, str] = {}

        if status == "failed":
            event_log.emit(
                "job.failed",
                level="warning",
                reason="required_llm_warning",
                warning_count=len(warnings),
            )
            return ReportJobResponse(
                job_id=job_id,
                batch_id=batch_id,
                status=status,
                bundle=bundle.model_dump(),
                sections=sections,
                ppt_sections=ppt_sections,
                llm_metadata=llm_metadata,
                artifacts=artifacts,
                warnings=warnings,
                logs_url=f"/api/v1/jobs/{job_id}/logs",
            )

        html = html_renderer.render(bundle, sections, language=request.language)
        html_path = output_dir / f"{job_id}.html"
        html_path.write_text(html, encoding="utf-8")
        artifacts["html"] = str(html_path)
        event_log.emit("artifact.written", artifact_type="html", path=str(html_path))

        if request.template_id:
            try:
                ppt_path = output_dir / f"{job_id}.pptx"
                render_ppt(bundle, ppt_sections or sections, request.template_id, str(ppt_path))
                artifacts["pptx"] = str(ppt_path)
                event_log.emit("artifact.written", artifact_type="pptx", path=str(ppt_path))
            except Exception as exc:
                logger.exception("PPT rendering failed")
                warnings.append(f"PPT rendering skipped: {exc}")
                event_log.emit(
                    "artifact.failed",
                    level="warning",
                    artifact_type="pptx",
                    error_type=type(exc).__name__,
                    error=str(exc),
                )

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
                event_log.emit("artifact.written", artifact_type="pdf", path=str(pdf_path))
            except Exception as exc:
                logger.exception("PDF rendering failed")
                warnings.append(f"PDF rendering skipped: {exc}")
                event_log.emit(
                    "artifact.failed",
                    level="warning",
                    artifact_type="pdf",
                    error_type=type(exc).__name__,
                    error=str(exc),
                )

        event_log.emit(
            "job.completed",
            status=status,
            artifact_types=sorted(artifacts.keys()),
            warning_count=len(warnings),
        )
        return ReportJobResponse(
            job_id=job_id,
            batch_id=batch_id,
            status=status,
            bundle=bundle.model_dump(),
            sections=sections,
            ppt_sections=ppt_sections,
            llm_metadata=llm_metadata,
            artifacts=artifacts,
            warnings=warnings,
            logs_url=f"/api/v1/jobs/{job_id}/logs",
        )
    except Exception as exc:
        event_log.emit(
            "job.exception",
            level="error",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise


@app.post("/api/v1/jobs", response_model=ReportJobResponse)
async def create_report_job(request: ReportJobRequest):
    """
    Demo-ready synchronous job path.

    The production design can move this behind the Postgres queue, but for a POC
    recording it proves the full Bundle -> Narrative -> HTML/PPT flow in one call.
    """
    return await execute_report_job(request)


@app.post("/api/v1/batches", response_model=BatchReportJobResponse)
async def create_report_batch(request: BatchReportJobRequest):
    ensure_template_registry_loaded()
    languages = dedupe_preserving_order(request.languages)
    if not languages:
        languages = ["en-US"]

    batch_id = str(uuid4())
    batch_log = StructuredEventLogger(
        settings.LOGS_DIR,
        batch_id=batch_id,
        context={
            "wave_id": request.wave_id,
            "template_id": request.template_id,
        },
    )
    batch_log.emit(
        "batch.started",
        languages=languages,
        use_llm=request.use_llm,
        require_llm=request.require_llm,
        include_pdf=request.include_pdf,
    )

    child_job_ids = [str(uuid4()) for _ in languages]
    child_requests = [
        ReportJobRequest(
            wave_id=request.wave_id,
            language=language,
            template_id=request.template_id,
            use_llm=request.use_llm,
            require_llm=request.require_llm,
            include_pdf=request.include_pdf,
            output_dir=request.output_dir,
        )
        for language in languages
    ]
    results = await asyncio.gather(
        *[
            execute_report_job(child_request, batch_id=batch_id, job_id=job_id)
            for child_request, job_id in zip(child_requests, child_job_ids)
        ],
        return_exceptions=True,
    )

    children = []
    for language, job_id, result in zip(languages, child_job_ids, results):
        if isinstance(result, Exception):
            child_log = batch_log.child(job_id=job_id, context={"language": language})
            child_log.emit(
                "job.batch_exception",
                level="error",
                error_type=type(result).__name__,
                error=str(result),
            )
            children.append(
                BatchChildJobResponse(
                    language=language,
                    job_id=job_id,
                    status="failed",
                    warnings=[str(result)],
                    logs_url=f"/api/v1/jobs/{job_id}/logs",
                )
            )
            continue

        children.append(
            BatchChildJobResponse(
                language=language,
                job_id=result.job_id,
                status=result.status,
                artifacts=result.artifacts,
                warnings=result.warnings,
                llm_metadata=result.llm_metadata,
                logs_url=result.logs_url,
            )
        )

    status = "completed" if all(child.status == "completed" for child in children) else "failed"
    batch_log.emit(
        "batch.completed",
        status=status,
        child_statuses={child.language: child.status for child in children},
    )
    return BatchReportJobResponse(
        batch_id=batch_id,
        status=status,
        wave_id=request.wave_id,
        template_id=request.template_id,
        languages=languages,
        children=children,
        logs_url=f"/api/v1/batches/{batch_id}/logs",
    )


@app.get("/api/v1/batches/{batch_id}/logs")
def get_batch_logs(batch_id: str):
    return {"batch_id": batch_id, "events": read_jsonl(log_path("batches", batch_id))}


@app.get("/api/v1/jobs/{job_id}/logs")
def get_job_logs(job_id: str):
    return {"job_id": job_id, "events": read_jsonl(log_path("jobs", job_id))}
