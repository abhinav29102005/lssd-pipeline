"""Cluster simulator that can create 100+ virtual nodes."""

from __future__ import annotations

import asyncio
import logging

from src.cluster.node_manager import NodeManager
from src.utils.config import settings

logger = logging.getLogger(__name__)


class ClusterSimulator:
    """Registers many synthetic worker nodes and keeps them alive via heartbeats."""

    def __init__(self, node_manager: NodeManager) -> None:
        self.node_manager = node_manager
        self._running = False

    async def bootstrap(self, cluster_size: int | None = None) -> None:
        target = cluster_size or settings.cluster_size
        for i in range(1, target + 1):
            node_id = f"sim-node-{i:03d}"
            self.node_manager.register_node(
                node_id=node_id,
                cpu_cores=settings.default_node_cpu,
                memory_mb=settings.default_node_memory_mb,
            )
        logger.info("Cluster simulator bootstrapped", extra={"cluster_size": target})

    async def heartbeat_loop(self) -> None:
        """Continuously emits heartbeats for all simulated nodes."""
        self._running = True
        while self._running:
            for i in range(1, settings.cluster_size + 1):
                self.node_manager.update_heartbeat(f"sim-node-{i:03d}")
            await asyncio.sleep(settings.heartbeat_interval)

    def stop(self) -> None:
        self._running = False
