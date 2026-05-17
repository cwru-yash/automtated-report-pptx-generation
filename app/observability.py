import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable

logger = logging.getLogger(__name__)


class StructuredEventLogger:
    def __init__(
        self,
        logs_dir: str,
        *,
        batch_id: str | None = None,
        job_id: str | None = None,
        context: Dict[str, Any] | None = None,
    ):
        self.logs_dir = Path(logs_dir)
        self.batch_id = batch_id
        self.job_id = job_id
        self.context = context or {}

    def child(
        self,
        *,
        job_id: str,
        context: Dict[str, Any] | None = None,
    ) -> "StructuredEventLogger":
        merged_context = {**self.context, **(context or {})}
        return StructuredEventLogger(
            str(self.logs_dir),
            batch_id=self.batch_id,
            job_id=job_id,
            context=merged_context,
        )

    def emit(self, event: str, *, level: str = "info", **details: Any) -> Dict[str, Any]:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event": event,
            "batch_id": self.batch_id,
            "job_id": self.job_id,
            **self.context,
            **details,
        }
        self._write_event(payload)
        getattr(logger, level if hasattr(logger, level) else "info")(
            "%s batch_id=%s job_id=%s details=%s",
            event,
            self.batch_id,
            self.job_id,
            details,
        )
        return payload

    def _write_event(self, payload: Dict[str, Any]) -> None:
        for path in self._event_paths():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _event_paths(self) -> Iterable[Path]:
        yield self.logs_dir / "system.jsonl"
        if self.batch_id:
            yield self.logs_dir / "batches" / f"{self.batch_id}.jsonl"
        if self.job_id:
            yield self.logs_dir / "jobs" / f"{self.job_id}.jsonl"


def read_jsonl(path: Path) -> list[Dict[str, Any]]:
    if not path.is_file():
        return []
    events = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                events.append(json.loads(stripped))
    return events
