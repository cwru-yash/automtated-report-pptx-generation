from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


BlockType = Literal[
    "heading",
    "paragraph",
    "bullet_list",
    "ordered_list",
    "quote",
    "metric_card",
    "table",
    "chart_placeholder",
    "image",
    "two_column",
    "three_column",
    "callout",
    "divider",
    "footnote",
    "source_note",
]

SlideLayoutType = Literal[
    "title",
    "executive_summary",
    "context",
    "finding",
    "recommendation",
    "limitation",
    "appendix",
]


class DeckValidationError(ValueError):
    """Raised when recursive deck JSON is malformed."""


class DeckTheme(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = "executive-light"
    font_family: str = "Aptos"
    primary_color: str = "#17324d"
    accent_color: str = "#c8a45d"
    background_color: str = "#f7f8f5"
    surface_color: str = "#ffffff"
    text_color: str = "#17202a"
    muted_text_color: str = "#5f6b7a"


class DeckColumn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: int = Field(default=50, ge=1, le=100)
    content: list["ContentBlock"] = Field(default_factory=list)


class ContentBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: BlockType
    text: str | None = None
    level: int | None = Field(default=None, ge=1, le=3)
    items: list[str] = Field(default_factory=list)
    label: str | None = None
    value: str | int | float | None = None
    helper: str | None = None
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str | int | float]] = Field(default_factory=list)
    chart_ref: str | None = None
    title: str | None = None
    src: str | None = None
    alt: str | None = None
    columns: list[DeckColumn] = Field(default_factory=list)
    variant: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_by_type(self) -> Self:
        if self.type == "heading":
            self._require_text("heading")
            if self.level is None:
                self.level = 2
        elif self.type in {"paragraph", "quote", "callout", "footnote", "source_note"}:
            self._require_text(self.type)
        elif self.type in {"bullet_list", "ordered_list"} and not self.items:
            raise ValueError(f"{self.type} block requires at least one item")
        elif self.type == "metric_card":
            if self.label is None or self.value is None:
                raise ValueError("metric_card block requires label and value")
        elif self.type == "table":
            if not self.headers or not self.rows:
                raise ValueError("table block requires headers and rows")
        elif self.type == "chart_placeholder":
            if not self.chart_ref:
                raise ValueError("chart_placeholder block requires chart_ref")
        elif self.type == "image":
            if not self.src:
                raise ValueError("image block requires src")
        elif self.type == "two_column":
            self._validate_column_count(2)
        elif self.type == "three_column":
            self._validate_column_count(3)
        return self

    def _require_text(self, block_name: str) -> None:
        if not self.text:
            raise ValueError(f"{block_name} block requires text")

    def _validate_column_count(self, expected: int) -> None:
        if len(self.columns) != expected:
            raise ValueError(f"{self.type} block requires {expected} columns")


class DeckSlideDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: SlideLayoutType
    title: str
    speaker_notes: str = ""
    content: list[ContentBlock] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class DeckDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deck_id: str
    title: str
    source_wave_id: str = ""
    source_project: str = ""
    theme: DeckTheme = Field(default_factory=DeckTheme)
    slides: list[DeckSlideDocument] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_has_slides(self) -> Self:
        if not self.slides:
            raise ValueError("DeckDocument requires at least one slide")
        return self


DeckColumn.model_rebuild()
ContentBlock.model_rebuild()
