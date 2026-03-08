"""Node domain model used by scheduler services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.database.models import NodeStatus


@dataclass(slots=True)
class Node:
    """In-memory view of a cluster node."""

    node_id: str
    cpu_cores: int
    memory_mb: int
    status: NodeStatus = NodeStatus.AVAILABLE
    current_jobs: int = 0
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)

    def can_run(self, required_cpu: int, required_memory: int) -> bool:
        """Return True when node has enough available resources."""
        if self.status not in {NodeStatus.AVAILABLE, NodeStatus.BUSY}:
            return False
        return self.cpu_cores >= required_cpu and self.memory_mb >= required_memory
