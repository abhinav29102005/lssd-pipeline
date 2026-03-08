"""Failure detector loop for stale heartbeats."""

from __future__ import annotations

import asyncio
import logging

from src.cluster.node_manager import NodeManager
from src.fault_tolerance.recovery_manager import RecoveryManager
from src.utils.config import settings

logger = logging.getLogger(__name__)


class FailureDetector:
    """Detects failed nodes and triggers recovery workflows."""

    def __init__(self, node_manager: NodeManager, recovery_manager: RecoveryManager) -> None:
        self.node_manager = node_manager
        self.recovery_manager = recovery_manager

    async def run(self) -> None:
        while True:
            failed_nodes = self.node_manager.mark_failed_nodes_and_recover_jobs(settings.heartbeat_timeout)
            if failed_nodes:
                self.recovery_manager.recover_jobs_from_failed_nodes(failed_nodes)
                logger.error("Failure detector handled stale nodes", extra={"failed_nodes": failed_nodes})
            await asyncio.sleep(max(1.0, settings.heartbeat_interval))
