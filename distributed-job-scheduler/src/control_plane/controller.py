"""Kubernetes-style cluster controller.

Runs a reconciliation loop that compares *desired* cluster state (based on
Raft-replicated log entries) with *actual* DB state and takes corrective
actions: registering nodes, draining / removing stale nodes, adjusting
scheduling parameters, etc.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from src.cluster.node_manager import NodeManager
from src.control_plane.leader_election import LeaderElection
from src.database.db import get_db_session
from src.database.models import NodeModel, NodeStatus
from src.utils.config import settings

logger = logging.getLogger(__name__)


class ClusterController:
    """Kubernetes-style controller with a reconcile loop.

    Only the **leader** node performs reconciliation.  Followers stay idle
    until they win an election.
    """

    def __init__(
        self,
        leader_election: LeaderElection,
        node_manager: NodeManager,
        reconcile_interval: float = 5.0,
    ) -> None:
        self.leader_election = leader_election
        self.node_manager = node_manager
        self.reconcile_interval = reconcile_interval
        self._running = False

        # Desired state that gets replicated through Raft proposals
        self.desired_cluster_size: int = settings.cluster_size
        self.desired_algorithm: str = settings.scheduler_algorithm

    # ── reconciliation ───────────────────────────────────────────────────

    def _reconcile(self) -> dict[str, Any]:
        """Compare desired vs actual state and apply corrective actions.

        Returns a summary dict of actions taken.
        """
        actions: dict[str, Any] = {"scaled_up": 0, "drained": 0, "recovered": 0}

        with get_db_session() as session:
            from sqlalchemy import func, select

            actual_total = session.scalar(select(func.count()).select_from(NodeModel)) or 0
            failed_nodes = (
                session.execute(
                    select(NodeModel).where(NodeModel.status == NodeStatus.FAILED)
                )
                .scalars()
                .all()
            )

            # ── Scale up: register additional simulated nodes ────────
            if actual_total < self.desired_cluster_size:
                deficit = self.desired_cluster_size - actual_total
                for i in range(deficit):
                    new_id = f"ctrl-node-{actual_total + i + 1:04d}"
                    self.node_manager.register_node(
                        node_id=new_id,
                        cpu_cores=settings.default_node_cpu,
                        memory_mb=settings.default_node_memory_mb,
                    )
                    actions["scaled_up"] += 1

            # ── Scale down: drain excess nodes ───────────────────────
            if actual_total > self.desired_cluster_size:
                excess = actual_total - self.desired_cluster_size
                available = (
                    session.execute(
                        select(NodeModel)
                        .where(NodeModel.status == NodeStatus.AVAILABLE)
                        .order_by(NodeModel.node_id.desc())
                        .limit(excess)
                    )
                    .scalars()
                    .all()
                )
                for node in available:
                    node.status = NodeStatus.DRAINING
                    actions["drained"] += 1

            # ── Recover nodes that have been failed too long ─────────
            #    (reset them to available so workers can re-register)
            for node in failed_nodes:
                elapsed = (datetime.utcnow() - node.last_heartbeat).total_seconds()
                if elapsed > settings.heartbeat_timeout * 5:
                    # Remove permanently-dead nodes
                    session.delete(node)
                    actions["recovered"] += 1

        return actions

    # ── Raft-backed desired state mutations ──────────────────────────────

    def set_desired_cluster_size(self, size: int) -> bool:
        """Propose a cluster resize through the Raft log."""
        ok = self.leader_election.propose(
            "set_cluster_size",
            {"cluster_size": size},
        )
        if ok:
            self.desired_cluster_size = size
            logger.info("Proposed cluster resize", extra={"desired_size": size})
        return ok

    def set_desired_algorithm(self, algorithm: str) -> bool:
        """Propose a scheduling algorithm change through the Raft log."""
        ok = self.leader_election.propose(
            "set_algorithm",
            {"algorithm": algorithm},
        )
        if ok:
            self.desired_algorithm = algorithm
            logger.info("Proposed algorithm change", extra={"algorithm": algorithm})
        return ok

    # ── main loop ────────────────────────────────────────────────────────

    async def run(self) -> None:
        """Run the controller reconciliation loop."""
        self._running = True
        logger.info("Cluster controller started")

        while self._running:
            if self.leader_election.is_leader():
                try:
                    actions = self._reconcile()
                    if any(v > 0 for v in actions.values()):
                        logger.info(
                            "Reconciliation complete",
                            extra={"actions": actions},
                        )
                except Exception:
                    logger.exception("Reconciliation failed")

                # Apply any committed Raft commands to desired state
                leader = self.leader_election.leader_node()
                if leader:
                    for entry in leader.state_machine:
                        if entry["command"] == "set_cluster_size":
                            self.desired_cluster_size = entry["data"].get(
                                "cluster_size", self.desired_cluster_size
                            )
                        elif entry["command"] == "set_algorithm":
                            self.desired_algorithm = entry["data"].get(
                                "algorithm", self.desired_algorithm
                            )

            await asyncio.sleep(self.reconcile_interval)

    def stop(self) -> None:
        """Stop the controller loop."""
        self._running = False

    # ── diagnostics ──────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        """Return controller state snapshot."""
        return {
            "is_leader": self.leader_election.is_leader(),
            "current_leader": self.leader_election.current_leader,
            "desired_cluster_size": self.desired_cluster_size,
            "desired_algorithm": self.desired_algorithm,
            "raft_cluster": self.leader_election.cluster_status(),
        }
