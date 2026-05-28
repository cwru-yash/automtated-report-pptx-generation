from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from app.bundle.schema import AnalysisBundle
from app.deck.schema import DeckPlan, DeckSlide, DeckValidationError, EvidenceItem

NUMBER_RE = re.compile(r"(?<![A-Za-z0-9-])-?\d+(?:\.\d+)?(?![A-Za-z0-9-])")


class EvidenceRegistry:
    """
    Holds the numeric facts that slide copy is allowed to use.

    The regex intentionally ignores numbers embedded in activity codes, so
    labels like US10 or ACT-010 do not become unsupported numeric claims.
    """

    def __init__(self, items: Iterable[EvidenceItem] | None = None):
        self.items = list(items or [])
        self._approved_numbers = self._collect_numbers(self.items)

    @classmethod
    def from_bundle(
        cls,
        bundle: AnalysisBundle,
        extra_items: Iterable[EvidenceItem] | None = None,
    ) -> "EvidenceRegistry":
        items = list(extra_items or [])
        registry = cls(items)
        registry._approved_numbers.update(registry._collect_numbers(bundle.metrics))
        registry._approved_numbers.update(registry._collect_numbers(bundle.analysis_results))
        return registry

    def validate_deck_plan(self, deck_plan: DeckPlan) -> None:
        unsupported: list[str] = []
        for slide in deck_plan.slides:
            unsupported.extend(self._unsupported_numbers_for_slide(slide))

        if unsupported:
            unique = sorted(set(unsupported), key=unsupported.index)
            raise DeckValidationError(
                "Unsupported numeric claim(s) in deck plan: " + ", ".join(unique)
            )

    def _unsupported_numbers_for_slide(self, slide: DeckSlide) -> list[str]:
        unsupported: list[str] = []
        text_parts = [
            slide.title,
            slide.subtitle,
            slide.speaker_notes,
            *slide.bullets,
            *slide.evidence,
        ]
        for text in text_parts:
            for raw_number in NUMBER_RE.findall(text or ""):
                if self._is_ignorable_number(raw_number):
                    continue
                if self._normalize_number(raw_number) not in self._approved_numbers:
                    unsupported.append(raw_number)
        return unsupported

    @classmethod
    def _collect_numbers(cls, value: Any) -> set[str]:
        if isinstance(value, bool) or value is None:
            return set()
        if isinstance(value, EvidenceItem):
            return cls._collect_numbers(value.value)
        if isinstance(value, (int, float, Decimal)):
            return {cls._normalize_number(str(value))}
        if isinstance(value, dict):
            numbers: set[str] = set()
            for child in value.values():
                numbers.update(cls._collect_numbers(child))
            return numbers
        if isinstance(value, list | tuple | set):
            numbers: set[str] = set()
            for child in value:
                numbers.update(cls._collect_numbers(child))
            return numbers
        return set()

    @staticmethod
    def _normalize_number(value: str) -> str:
        try:
            return str(Decimal(value).normalize())
        except (InvalidOperation, ValueError):
            return value

    @staticmethod
    def _is_ignorable_number(raw_number: str) -> bool:
        unsigned = raw_number.lstrip("-")
        if "." not in unsigned and len(unsigned) < 3 and int(raw_number) < 10:
            return True
        if len(unsigned) == 4 and unsigned.startswith("20"):
            return True
        return False
