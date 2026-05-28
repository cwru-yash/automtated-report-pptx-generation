from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field, ValidationError

from app.bundle.assembler import BundleAssembler
from app.config import settings
from app.data.provider import get_provider
from app.deck.ai_outline import (
    AIOutlineError,
    AIOutlineProviderNotConfigured,
    DeckOutline,
    generate_ai_outline,
    get_ai_outline_provider,
)
from app.deck.builder import ReportDeckBuilder
from app.deck.extractor import FindingExtractor
from app.deck.html_preview import render_deck_document_html
from app.deck.layout_mapper import DeckLayoutMapper
from app.deck.layout_schema import DeckDocument
from app.deck.repository import DeckRepository, deck_project_to_response
from app.deck.schema import DeckDataQualityError, DeckValidationError
from app.renderers.ppt import render_deck_document_ppt
from app.templates.registry import init_registry, registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/decks", tags=["decks"])


class CreateDeckFromWaveRequest(BaseModel):
    wave_id: str = Field(..., description="Completed Decomposer wave ID")
    language: str = Field(default="en-US")
    audience: str = Field(default="executive stakeholders")
    tone: str = Field(default="consulting")
    allow_partial: bool = Field(default=False)


class SaveDeckRequest(BaseModel):
    deck: DeckDocument


class ValidateDeckRequest(BaseModel):
    deck: dict[str, Any]


class DeckProjectResponse(BaseModel):
    id: str
    source_wave_id: str
    title: str
    status: str
    deck_json: dict[str, Any]
    outline_json: dict[str, Any] = Field(default_factory=dict)
    theme_json: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class AIOutlineResponse(BaseModel):
    outline: DeckOutline
    provider: str = "ai"


class AcceptAIOutlineRequest(CreateDeckFromWaveRequest):
    outline: DeckOutline


def safe_artifact_stem(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)


def ensure_template_registry_loaded() -> None:
    if not registry.list_templates():
        init_registry(settings.TEMPLATES_DIR)


def require_editor_token(x_deck_edit_token: str | None = Header(default=None)) -> None:
    if not settings.DECK_EDITOR_TOKEN:
        logger.warning("DECK_EDITOR_TOKEN is not configured; allowing local editor write.")
        return
    if x_deck_edit_token != settings.DECK_EDITOR_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid deck editor token")


@router.get("/demo", response_model=DeckProjectResponse)
async def get_demo_deck() -> DeckProjectResponse:
    repository = DeckRepository()
    demo = DeckLayoutMapper().demo_deck()
    existing = await repository.get(demo.deck_id)
    row = existing or await repository.create(demo, status="demo")
    return DeckProjectResponse(**deck_project_to_response(row))


@router.post("/from-wave", response_model=DeckProjectResponse)
async def create_deck_from_wave(
    request: CreateDeckFromWaveRequest,
    x_deck_edit_token: str | None = Header(default=None),
) -> DeckProjectResponse:
    require_editor_token(x_deck_edit_token)
    provider = get_provider(settings)
    try:
        result = await ReportDeckBuilder(provider=provider).build_from_wave(
            wave_id=request.wave_id,
            language=request.language,
            audience=request.audience,
            tone=request.tone,
            allow_partial=request.allow_partial,
        )
    except (DeckDataQualityError, DeckValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return DeckProjectResponse(**deck_project_to_response(result.row))


@router.post("/from-wave/outline/ai", response_model=AIOutlineResponse)
async def create_ai_outline_from_wave(
    request: CreateDeckFromWaveRequest,
    x_deck_edit_token: str | None = Header(default=None),
) -> AIOutlineResponse:
    require_editor_token(x_deck_edit_token)
    provider = get_provider(settings)
    try:
        wave_data = provider.get_wave_data(request.wave_id)
        bundle = await BundleAssembler().build_bundle(
            request.wave_id,
            request.language,
            wave_data=wave_data,
        )
        context = FindingExtractor().extract(
            bundle,
            wave_data,
            allow_partial=request.allow_partial,
        )
        outline = await generate_ai_outline(
            context,
            provider=get_ai_outline_provider(),
            audience=request.audience,
        )
    except (DeckDataQualityError, DeckValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AIOutlineProviderNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AIOutlineError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AIOutlineResponse(outline=outline)


@router.post("/from-wave/outline/accept", response_model=DeckProjectResponse)
async def accept_ai_outline_from_wave(
    request: AcceptAIOutlineRequest,
    x_deck_edit_token: str | None = Header(default=None),
) -> DeckProjectResponse:
    require_editor_token(x_deck_edit_token)
    provider = get_provider(settings)
    try:
        result = await ReportDeckBuilder(provider=provider).build_from_accepted_outline(
            wave_id=request.wave_id,
            outline=request.outline,
            language=request.language,
            audience=request.audience,
            tone=request.tone,
            allow_partial=request.allow_partial,
        )
    except (DeckDataQualityError, DeckValidationError, AIOutlineError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return DeckProjectResponse(**deck_project_to_response(result.row))


@router.post("/validate")
async def validate_deck(request: ValidateDeckRequest) -> dict[str, Any]:
    try:
        deck = DeckDocument.model_validate(request.deck)
    except ValidationError as exc:
        return {
            "valid": False,
            "errors": exc.errors(),
        }
    return {
        "valid": True,
        "deck_id": deck.deck_id,
        "slide_count": len(deck.slides),
    }


@router.get("/{deck_id}/export/pptx")
async def export_deck_pptx(
    deck_id: str,
    template_id: str = "client_cvc_master",
) -> FileResponse:
    row = await DeckRepository().get(deck_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Deck not found")

    try:
        deck = DeckDocument.model_validate(row.deck_json)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    try:
        ensure_template_registry_loaded()
        output_dir = Path("artifacts")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"{safe_artifact_stem(deck_id)}_editable.pptx"
        render_deck_document_ppt(deck, template_id, str(output_path))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}") from exc
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"{safe_artifact_stem(deck_id)}.pptx",
    )


@router.get("/{deck_id}/preview/html", response_class=HTMLResponse)
async def preview_deck_html(deck_id: str) -> HTMLResponse:
    row = await DeckRepository().get(deck_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Deck not found")

    try:
        deck = DeckDocument.model_validate(row.deck_json)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    return HTMLResponse(render_deck_document_html(deck))


@router.get("/{deck_id}", response_model=DeckProjectResponse)
async def get_deck(deck_id: str) -> DeckProjectResponse:
    row = await DeckRepository().get(deck_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Deck not found")
    return DeckProjectResponse(**deck_project_to_response(row))


@router.put("/{deck_id}", response_model=DeckProjectResponse)
async def save_deck(
    deck_id: str,
    request: SaveDeckRequest,
    x_deck_edit_token: str | None = Header(default=None),
) -> DeckProjectResponse:
    require_editor_token(x_deck_edit_token)
    deck = request.deck
    if deck.deck_id != deck_id:
        raise HTTPException(status_code=400, detail="Deck ID mismatch")

    row = await DeckRepository().update_deck(deck_id, deck)
    if row is None:
        raise HTTPException(status_code=404, detail="Deck not found")
    return DeckProjectResponse(**deck_project_to_response(row))
