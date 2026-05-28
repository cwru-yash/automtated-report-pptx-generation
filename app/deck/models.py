from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, JSON, String

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DeckProject(Base):
    __tablename__ = "deck_projects"

    id = Column(String, primary_key=True, index=True)
    source_wave_id = Column(String, index=True)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="draft", index=True)
    deck_json = Column(JSON, nullable=False)
    outline_json = Column(JSON, nullable=True)
    theme_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
