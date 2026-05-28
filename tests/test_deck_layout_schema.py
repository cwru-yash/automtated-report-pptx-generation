import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.deck.layout_mapper import DeckLayoutMapper
from app.deck.layout_schema import ContentBlock, DeckDocument


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "canonical_deck_document.json"


def test_demo_recursive_deck_json_validates():
    deck = DeckLayoutMapper().demo_deck()

    parsed = DeckDocument.model_validate(deck.model_dump(mode="json"))

    assert parsed.deck_id == "demo_recursive_deck"
    assert parsed.slides


def test_canonical_deck_document_fixture_validates():
    deck = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    parsed = DeckDocument.model_validate(deck)

    assert parsed.deck_id == "canonical_deck_fixture"
    assert parsed.slides[1].content[0].type == "two_column"


def test_invalid_block_type_is_rejected():
    deck = DeckLayoutMapper().demo_deck().model_dump(mode="json")
    deck["slides"][0]["content"][0]["type"] = "unsupported"

    with pytest.raises(ValidationError):
        DeckDocument.model_validate(deck)


def test_nested_two_column_content_validates():
    block = ContentBlock(
        id="cols",
        type="two_column",
        columns=[
            {
                "width": 50,
                "content": [
                    {"id": "h1", "type": "heading", "level": 2, "text": "Left"}
                ],
            },
            {
                "width": 50,
                "content": [
                    {"id": "p1", "type": "paragraph", "text": "Right"}
                ],
            },
        ],
    )

    assert block.columns[0].content[0].type == "heading"
