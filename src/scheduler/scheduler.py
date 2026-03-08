"""Central scheduler orchestration loop."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime

from sqlalchemy import func, select

from src.cluster.node_manager import NodeManager
from src.database.db import get_db_session
from src.database.models import ClusterMetricModel, JobModel, JobStatus
from src.scheduler.job_queue import JobQueue
from src.scheduler.scheduling_algorithms import SchedulingAlgorithms
from src.utils.config import settings

logger = logging.getLogger(__name__)


class DistributedScheduler:
    """Schedules pending jobs onto available nodes."""

    def __init__(self, job_queue: JobQueue, node_manager: NodeManager) -> None:
        self.job_queue = job_queue
        self.node_manager = node_manager
        self.algorithms = SchedulingAlgorithms()
        self._running = False

    async def scheduling_loop(self) -> None:
        self._running = True
        while self._running:
            queue_job = self.job_queue.dequeue_pending()
            if not queue_job:
                await asyncio.sleep(settings.schedule_interval_seconds)
                continue

            available_nodes = [
                n
                for n in self.node_manager.available_nodes()
                if n.cpu_cores >= queue_job.required_cpu and n.memory_mb >= queue_job.required_memory
            ]

            selected = self.algorithms.select_node(settings.scheduler_algorithm, available_nodes)
            if not selected:
                self.job_queue.enqueue_pending(queue_job)
                await asyncio.sleep(settings.schedule_interval_seconds)
                continue

            with get_db_session() as session:
                job = session.get(JobModel, uuid.UUID(queue_job.job_id))
                if not job or job.status in {JobStatus.CANCELLED, JobStatus.COMPLETED}:
                    continue
                job.status = JobStatus.RUNNING
                job.start_time = datetime.utcnow()
                job.node_assigned = selected.node_id

            self.node_manager.increment_jobs(selected.node_id)
            self.job_queue.push_running(queue_job.job_id)
            self.job_queue.publish_assignment(selected.node_id, queue_job.job_id)

            logger.info(
                "Assigned job to node",
                extra={"job_id": queue_job.job_id, "node_id": selected.node_id},
            )

            await asyncio.sleep(settings.schedule_interval_seconds)

    async def metrics_loop(self) -> None:
        """Persist cluster status snapshots."""
        while True:
            counts = self.node_manager.cluster_counts()
            queue_size = self.job_queue.pending_size()
            running_jobs = self.job_queue.running_size()
            completed_jobs = self.job_queue.completed_size()
            utilization = 0.0
            if counts["total_nodes"] > 0:
                utilization = min(1.0, running_jobs / max(1, counts["total_nodes"]))

            with get_db_session() as session:
                running_from_db = (
                    session.scalar(select(func.count()).select_from(JobModel).where(JobModel.status == JobStatus.RUNNING))
                    or 0
                )
                session.add(
                    ClusterMetricModel(
                        total_nodes=counts["total_nodes"],
                        active_nodes=counts["active_nodes"],
                        failed_nodes=counts["failed_nodes"],
                        running_jobs=int(running_from_db),
                        completed_jobs=completed_jobs,
                        queue_size=queue_size,
                        cluster_utilization=utilization,
                    )
                )

            await asyncio.sleep(2.0)

    def stop(self) -> None:
        self._running = False


async def main() -> None:
    """Run the scheduler service standalone."""
    import logging
    from src.cluster.node_manager import NodeManager
    from src.scheduler.job_queue import JobQueue
    from src.utils.config import settings

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    node_manager = NodeManager()
    job_queue = JobQueue()
    scheduler = DistributedScheduler(job_queue, node_manager)

    # Run both scheduling and metrics loops
    await asyncio.gather(
        scheduler.scheduling_loop(),
        scheduler.metrics_loop(),
    )


if __name__ == "__main__":
    asyncio.run(main())
