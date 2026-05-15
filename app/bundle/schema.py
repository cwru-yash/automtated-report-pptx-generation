from typing import Any, Dict

from pydantic import BaseModel, Field


class AnalysisBundle(BaseModel):
    wave_id: str = Field(..., description="The unique identifier for the wave")
    language: str = Field(..., description="The language code (e.g., pt-BR, en-US)")
    metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="Dictionary of metric names to values",
    )
    analysis_results: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dictionary of findings from analysis runs",
    )
