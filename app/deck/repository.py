from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.database import AsyncSessionLocal
from app.deck.layout_schema import DeckDocument
from app.deck.models import DeckProject


class DeckRepository:
    def __init__(self, session_maker: async_sessionmaker = AsyncSessionLocal):
        self.session_maker = session_maker

    async def create(
        self,
        deck: DeckDocument,
        *,
        outline_json: dict[str, Any] | None = None,
        status: str = "draft",
    ) -> DeckProject:
        async with self.session_maker() as session:
            row = DeckProject(
                id=deck.deck_id,
                source_wave_id=deck.source_wave_id,
                title=deck.title,
                status=status,
                deck_json=deck.model_dump(mode="json"),
                outline_json=outline_json or {},
                theme_json=deck.theme.model_dump(mode="json"),
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row

    async def get(self, deck_id: str) -> DeckProject | None:
        async with self.session_maker() as session:
            result = await session.execute(
                select(DeckProject).where(
                    DeckProject.id == deck_id,
                    DeckProject.deleted_at.is_(None),
                )
            )
            return result.scalar_one_or_none()

    async def update_deck(self, deck_id: str, deck: DeckDocument) -> DeckProject | None:
        async with self.session_maker() as session:
            result = await session.execute(
                select(DeckProject).where(
                    DeckProject.id == deck_id,
                    DeckProject.deleted_at.is_(None),
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None

            row.title = deck.title
            row.source_wave_id = deck.source_wave_id
            row.deck_json = deck.model_dump(mode="json")
            row.theme_json = deck.theme.model_dump(mode="json")
            row.updated_at = datetime.now(timezone.utc)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row


def deck_project_to_response(row: DeckProject) -> dict[str, Any]:
    return {
        "id": row.id,
        "source_wave_id": row.source_wave_id,
        "title": row.title,
        "status": row.status,
        "deck_json": row.deck_json,
        "outline_json": row.outline_json or {},
        "theme_json": row.theme_json or {},
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
    }
