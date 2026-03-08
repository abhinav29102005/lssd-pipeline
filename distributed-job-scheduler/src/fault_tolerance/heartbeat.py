"""Heartbeat sender for worker nodes."""

from __future__ import annotations

import asyncio

from src.cluster.node_manager import NodeManager
from src.utils.config import settings


class HeartbeatClient:
    """Periodically updates a node heartbeat timestamp."""

    def __init__(self, node_manager: NodeManager, node_id: str) -> None:
        self.node_manager = node_manager
        self.node_id = node_id

    async def run(self) -> None:
        while True:
            self.node_manager.update_heartbeat(self.node_id)
            await asyncio.sleep(settings.heartbeat_interval)
