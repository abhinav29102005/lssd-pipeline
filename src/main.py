"""Entry point for scheduler and simulator services."""

from __future__ import annotations

import asyncio
import logging

from src.cluster.cluster_simulator import ClusterSimulator
from src.cluster.node_manager import NodeManager
from src.control_plane.controller import ClusterController
from src.control_plane.leader_election import LeaderElection
from src.database.db import init_db
from src.fault_tolerance.failure_detector import FailureDetector
from src.fault_tolerance.recovery_manager import RecoveryManager
from src.scheduler.job_queue import JobQueue
from src.scheduler.scheduler import DistributedScheduler
from src.utils.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)


async def run_scheduler() -> None:
    """Initialize all scheduler-side background services."""
    init_db()

    node_manager = NodeManager()
    job_queue = JobQueue()
    scheduler = DistributedScheduler(job_queue, node_manager)
    recovery_manager = RecoveryManager(job_queue)
    failure_detector = FailureDetector(node_manager, recovery_manager)
    simulator = ClusterSimulator(node_manager)

    # ── Control Plane: Raft consensus + Kubernetes-style controller ──
    leader_election = LeaderElection(
        cluster_size=3,
        on_leader_change=lambda lid: logger.info(
            "Leader election result", extra={"leader": lid}
        ),
    )
    controller = ClusterController(
        leader_election=leader_election,
        node_manager=node_manager,
        reconcile_interval=5.0,
    )

    tasks = [
        asyncio.create_task(scheduler.scheduling_loop(), name="scheduling_loop"),
        asyncio.create_task(scheduler.metrics_loop(), name="metrics_loop"),
        asyncio.create_task(failure_detector.run(), name="failure_detector"),
        asyncio.create_task(leader_election.start(), name="raft_consensus"),
        asyncio.create_task(controller.run(), name="cluster_controller"),
    ]

    if settings.simulate_nodes:
        await simulator.bootstrap(settings.cluster_size)
        tasks.append(asyncio.create_task(simulator.heartbeat_loop(), name="simulator_heartbeat"))

    # TODO 1: Add auto-scaling compute nodes.
    # TODO 2: Implement GPU job scheduling.
    # TODO 3: Add priority queues with fairness guarantees.
    # TODO 4: Implement preemption of low priority jobs.
    # TODO 5: Add job dependency DAG support.
    # TODO 6: Add Kubernetes deployment support.
    # TODO 7: Implement job checkpointing and recovery.

    logger.info("Scheduler started with Raft consensus control plane")
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(run_scheduler())
