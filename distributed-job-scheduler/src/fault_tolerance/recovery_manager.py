"""Recovery logic for jobs affected by node failures."""

from __future__ import annotations

import logging

from src.database.db import get_db_session
from src.database.models import JobModel, JobStatus
from src.scheduler.job_queue import JobQueue, QueueJob

logger = logging.getLogger(__name__)


class RecoveryManager:
    """Re-queues jobs that need recovery after faults."""

    def __init__(self, job_queue: JobQueue) -> None:
        self.job_queue = job_queue

    def recover_jobs_from_failed_nodes(self, failed_node_ids: list[str]) -> int:
        recovered = 0
        if not failed_node_ids:
            return recovered

        with get_db_session() as session:
            jobs = (
                session.query(JobModel)
                .filter(JobModel.node_assigned.in_(failed_node_ids), JobModel.status == JobStatus.RETRY_WAIT)
                .all()
            )
            for job in jobs:
                if job.retry_count >= job.max_retries:
                    job.status = JobStatus.FAILED
                    self.job_queue.move_to_failed(str(job.job_id))
                    continue

                job.retry_count += 1
                job.status = JobStatus.PENDING
                job.node_assigned = None
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
                recovered += 1

        logger.warning("Recovered jobs after node failure", extra={"failed_nodes": failed_node_ids, "recovered": recovered})
        return recovered
