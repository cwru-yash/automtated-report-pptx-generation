import enum
from typing import Any, Dict, Optional

from sqlalchemy import Column, Enum, Integer, JSON, String
from sqlalchemy.future import select

from app.core.database import AsyncSessionLocal, Base


class JobStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    wave_id = Column(String, index=True)
    template_id = Column(String)
    language = Column(String)
    status = Column(Enum(JobStatus), default=JobStatus.pending, index=True)
    retry_count = Column(Integer, default=0)
    payload = Column(JSON)


class PostgresJobQueue:
    def __init__(self, session_maker=AsyncSessionLocal):
        self.session_maker = session_maker

    async def enqueue_job(
        self,
        job_id: str,
        wave_id: str,
        template_id: str,
        language: str,
        payload: Dict[str, Any] | None = None,
    ) -> Job:
        async with self.session_maker() as session:
            job = Job(
                id=job_id,
                wave_id=wave_id,
                template_id=template_id,
                language=language,
                status=JobStatus.pending,
                payload=payload or {},
            )
            session.add(job)
            await session.commit()
            return job

    async def get_next_job(self) -> Optional[Job]:
        async with self.session_maker() as session:
            stmt = select(Job).where(Job.status == JobStatus.pending).limit(1)
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()
            if job:
                job.status = JobStatus.in_progress
                session.add(job)
                await session.commit()
                await session.refresh(job)
            return job

    async def update_job_status(self, job_id: str, status: JobStatus) -> Optional[Job]:
        async with self.session_maker() as session:
            stmt = select(Job).where(Job.id == job_id)
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()
            if job:
                job.status = status
                session.add(job)
                await session.commit()
                await session.refresh(job)
            return job
