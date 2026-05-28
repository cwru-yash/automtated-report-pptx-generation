from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.bundle.assembler import BundleAssembler
from app.bundle.schema import AnalysisBundle
from app.data.provider import WaveDataProvider
from app.deck.extractor import FindingExtractor
from app.deck.layout_mapper import DeckLayoutMapper
from app.deck.layout_schema import DeckDocument
from app.deck.models import DeckProject
from app.deck.planner import SlidePlanner
from app.deck.repository import DeckRepository
from app.deck.schema import DeckPlan, FindingsContext


@dataclass(frozen=True)
class ReportDeckBuildResult:
    """Artifacts created while turning one completed wave into an editable deck."""

    row: DeckProject
    bundle: AnalysisBundle
    findings_context: FindingsContext
    deck_plan: DeckPlan
    deck_document: DeckDocument


class ReportDeckBuilder:
    """
    Orchestrates the report-to-deck generation boundary.

    Upstream wave data remains read-only. The only write in this builder is the
    local editable DeckProject row created by the repository.
    """

    def __init__(
        self,
        *,
        provider: WaveDataProvider,
        bundle_assembler: BundleAssembler | None = None,
        finding_extractor: FindingExtractor | None = None,
        slide_planner: SlidePlanner | None = None,
        layout_mapper: DeckLayoutMapper | None = None,
        repository: DeckRepository | None = None,
    ) -> None:
        self.provider = provider
        self.bundle_assembler = bundle_assembler or BundleAssembler()
        self.finding_extractor = finding_extractor or FindingExtractor()
        self.slide_planner = slide_planner or SlidePlanner()
        self.layout_mapper = layout_mapper or DeckLayoutMapper()
        self.repository = repository or DeckRepository()

    async def build_from_wave(
        self,
        *,
        wave_id: str,
        language: str = "en-US",
        audience: str = "executive stakeholders",
        tone: str = "consulting",
        allow_partial: bool = False,
    ) -> ReportDeckBuildResult:
        wave_data = self.provider.get_wave_data(wave_id)
        bundle = await self.bundle_assembler.build_bundle(
            wave_id,
            language,
            wave_data=wave_data,
        )
        self._attach_provenance(bundle, wave_data)

        findings_context = self.finding_extractor.extract(
            bundle,
            wave_data,
            allow_partial=allow_partial,
        )
        deck_plan = self.slide_planner.create_plan(
            findings_context,
            bundle,
            audience=audience,
            tone=tone,
        )
        deck_document = self.layout_mapper.from_deck_plan(deck_plan)
        row = await self.repository.create(
            deck_document,
            outline_json=deck_plan.model_dump(mode="json"),
        )

        return ReportDeckBuildResult(
            row=row,
            bundle=bundle,
            findings_context=findings_context,
            deck_plan=deck_plan,
            deck_document=deck_document,
        )

    @staticmethod
    def _attach_provenance(bundle: AnalysisBundle, wave_data: dict[str, Any]) -> None:
        metadata = wave_data.get("metadata", {})
        bundle.gold_activity_version_id = metadata.get("gold_activity_version_id", "")
        bundle.analysis_run_id = metadata.get("analysis_run_id", "")
