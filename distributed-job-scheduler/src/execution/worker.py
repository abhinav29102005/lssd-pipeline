"""Worker process that executes assigned jobs."""

from __future__ import annotations

import asyncio
import logging
import os
import random
from datetime import datetime

from src.cluster.node_manager import NodeManager
from src.database.db import get_db_session
from src.database.models import JobModel, JobStatus
from src.execution.job_executor import JobExecutor
from src.fault_tolerance.heartbeat import HeartbeatClient
from src.scheduler.job_queue import JobQueue
from src.scheduler.retry_manager import RetryManager
from src.utils.config import settings

logger = logging.getLogger(__name__)


class WorkerNode:
    """Represents a worker service instance."""

    def __init__(self, node_id: str | None = None) -> None:
        self.node_id = node_id or os.getenv("NODE_ID") or os.getenv("HOSTNAME", "worker-unknown")
        self.queue = JobQueue()
        self.retry_manager = RetryManager(self.queue)
        self.node_manager = NodeManager()
        self.executor = JobExecutor()
        self.heartbeat_client = HeartbeatClient(self.node_manager, self.node_id)

    async def start(self) -> None:
        self.node_manager.register_node(
            node_id=self.node_id,
            cpu_cores=settings.default_node_cpu,
            memory_mb=settings.default_node_memory_mb,
        )
        await asyncio.gather(self.heartbeat_client.run(), self._work_loop())

    async def _work_loop(self) -> None:
        while True:
            job_id = self.queue.consume_assignment(self.node_id)
            if not job_id:
                await asyncio.sleep(settings.worker_poll_interval)
                continue

            with get_db_session() as session:
                job = session.get(JobModel, job_id)
                if not job or job.status != JobStatus.RUNNING:
                    self.queue.remove_running(job_id)
                    self.node_manager.decrement_jobs(self.node_id)
                    continue

            try:
                if random.random() < settings.failure_rate:
                    raise RuntimeError("Synthetic worker failure during execution")

                result = await asyncio.wait_for(
                    self.executor.execute(task_type=job.task_type, execution_time=job.execution_time),
                    timeout=settings.job_timeout,
                )

                with get_db_session() as session:
                    job = session.get(JobModel, job_id)
                    if not job:
                        continue
                    job.status = JobStatus.COMPLETED
                    job.completion_time = datetime.utcnow()
                    job.error_message = None

                self.queue.move_to_completed(job_id)
                logger.info("Job completed", extra={"job_id": job_id, "node_id": self.node_id, "result": result})

            except Exception as exc:  # noqa: BLE001
                with get_db_session() as session:
                    job = session.get(JobModel, job_id)
                    if job:
                        job.status = JobStatus.RETRY_WAIT
                        job.error_message = str(exc)
                        job.node_assigned = None

                self.queue.remove_running(job_id)
                logger.exception("Job execution failed", extra={"job_id": job_id, "node_id": self.node_id})
                await self.retry_manager.handle_retry(job_id, str(exc))
            finally:
                self.node_manager.decrement_jobs(self.node_id)
