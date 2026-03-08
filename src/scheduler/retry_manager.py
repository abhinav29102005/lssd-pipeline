"""Job retry policy with exponential backoff."""

from __future__ import annotations

import asyncio
import logging
import uuid

from src.database.db import get_db_session
from src.database.models import JobModel, JobStatus
from src.scheduler.job_queue import JobQueue, QueueJob
from src.utils.config import settings

logger = logging.getLogger(__name__)


class RetryManager:
    """Handles retry decisions and delayed requeueing."""

    def __init__(self, job_queue: JobQueue) -> None:
        self.job_queue = job_queue

    async def handle_retry(self, job_id: str, error_message: str) -> None:
        job_uuid = uuid.UUID(job_id)
        with get_db_session() as session:
            job = session.get(JobModel, job_uuid)
            if not job:
                return

            if job.retry_count >= job.max_retries:
                job.status = JobStatus.FAILED
                job.error_message = error_message
                self.job_queue.move_to_failed(str(job.job_id))
                logger.error(
                    "Job exceeded max retries",
                    extra={"job_id": str(job.job_id), "retry_count": job.retry_count},
                )
                return

            job.retry_count += 1
            job.status = JobStatus.RETRY_WAIT
            job.error_message = error_message
            delay = settings.base_retry_delay * (2 ** (job.retry_count - 1))

            logger.warning(
                "Scheduling retry",
                extra={"job_id": str(job.job_id), "retry_count": job.retry_count, "delay": delay},
            )

        await asyncio.sleep(delay)

        with get_db_session() as session:
            job = session.get(JobModel, job_uuid)
            if not job or job.status == JobStatus.CANCELLED:
                return
            job.status = JobStatus.PENDING
            self.job_queue.enqueue_pending(
                QueueJob(
                    job_id=str(job.job_id),
                    priority=job.priority,
                    required_cpu=job.required_cpu,
                    required_memory=job.required_memory,
                    task_type=job.task_type,
                    execution_time=job.execution_time,
                )
            )
