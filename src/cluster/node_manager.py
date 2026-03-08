"""Manages node registration and state transitions."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import func, select

from src.database.db import get_db_session
from src.database.models import JobModel, JobStatus, NodeModel, NodeStatus

logger = logging.getLogger(__name__)


class NodeManager:
    """CRUD and monitoring operations for cluster nodes."""

    def register_node(self, node_id: str, cpu_cores: int, memory_mb: int) -> NodeModel:
        with get_db_session() as session:
            node = session.get(NodeModel, node_id)
            if node is None:
                node = NodeModel(
                    node_id=node_id,
                    cpu_cores=cpu_cores,
                    memory_mb=memory_mb,
                    status=NodeStatus.AVAILABLE,
                    current_jobs=0,
                    last_heartbeat=datetime.utcnow(),
                )
                session.add(node)
                logger.info("Registered node", extra={"node_id": node_id})
            else:
                node.cpu_cores = cpu_cores
                node.memory_mb = memory_mb
                node.status = NodeStatus.AVAILABLE
                node.last_heartbeat = datetime.utcnow()
                logger.info("Updated node registration", extra={"node_id": node_id})
            session.flush()
            return node

    def update_heartbeat(self, node_id: str) -> None:
        with get_db_session() as session:
            node = session.get(NodeModel, node_id)
            if not node:
                return
            node.last_heartbeat = datetime.utcnow()
            if node.status == NodeStatus.FAILED:
                node.status = NodeStatus.AVAILABLE
                logger.warning("Recovered node after heartbeat", extra={"node_id": node_id})

    def set_node_status(self, node_id: str, status: NodeStatus) -> None:
        with get_db_session() as session:
            node = session.get(NodeModel, node_id)
            if node:
                node.status = status

    def increment_jobs(self, node_id: str) -> None:
        with get_db_session() as session:
            node = session.get(NodeModel, node_id)
            if node:
                node.current_jobs += 1
                node.status = NodeStatus.BUSY

    def decrement_jobs(self, node_id: str) -> None:
        with get_db_session() as session:
            node = session.get(NodeModel, node_id)
            if node:
                node.current_jobs = max(0, node.current_jobs - 1)
                if node.current_jobs == 0 and node.status != NodeStatus.FAILED:
                    node.status = NodeStatus.AVAILABLE

    def available_nodes(self) -> list[NodeModel]:
        with get_db_session() as session:
            result = session.execute(
                select(NodeModel).where(NodeModel.status.in_([NodeStatus.AVAILABLE, NodeStatus.BUSY]))
            )
            nodes = list(result.scalars().all())
            # Expunge so attributes remain accessible after the session closes
            for n in nodes:
                session.expunge(n)
            return nodes

    def mark_failed_nodes_and_recover_jobs(self, heartbeat_timeout_seconds: float) -> list[str]:
        """Mark stale nodes as failed and return impacted running jobs to be retried."""
        failed_nodes: list[str] = []
        cutoff = datetime.utcnow().timestamp() - heartbeat_timeout_seconds

        with get_db_session() as session:
            result = session.execute(select(NodeModel))
            nodes = result.scalars().all()
            for node in nodes:
                if node.last_heartbeat.timestamp() < cutoff and node.status != NodeStatus.FAILED:
                    node.status = NodeStatus.FAILED
                    failed_nodes.append(node.node_id)
                    logger.error("Detected failed node", extra={"node_id": node.node_id})

            if failed_nodes:
                running_jobs = session.execute(
                    select(JobModel).where(
                        JobModel.node_assigned.in_(failed_nodes),
                        JobModel.status == JobStatus.RUNNING,
                    )
                ).scalars().all()
                for job in running_jobs:
                    job.status = JobStatus.RETRY_WAIT
                    job.node_assigned = None
                    job.error_message = "Node failure detected"

        return failed_nodes

    def cluster_counts(self) -> dict[str, int]:
        with get_db_session() as session:
            total = session.scalar(select(func.count()).select_from(NodeModel)) or 0
            active = (
                session.scalar(
                    select(func.count()).select_from(NodeModel).where(NodeModel.status != NodeStatus.FAILED)
                )
                or 0
            )
            failed = session.scalar(
                select(func.count()).select_from(NodeModel).where(NodeModel.status == NodeStatus.FAILED)
            ) or 0
            return {"total_nodes": total, "active_nodes": active, "failed_nodes": failed}
