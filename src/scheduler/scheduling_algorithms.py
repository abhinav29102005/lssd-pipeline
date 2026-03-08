"""Scheduling strategy implementations."""

from __future__ import annotations

from itertools import cycle
from threading import Lock

from src.database.models import NodeModel, NodeStatus


class SchedulingAlgorithms:
    """Collection of scheduling strategies."""

    def __init__(self) -> None:
        self._round_robin_cycle = None
        self._rr_lock = Lock()

    @staticmethod
    def first_come_first_serve(nodes: list[NodeModel]) -> NodeModel | None:
        for node in nodes:
            if node.status in {NodeStatus.AVAILABLE, NodeStatus.BUSY}:
                return node
        return None

    @staticmethod
    def priority_scheduling(nodes: list[NodeModel]) -> NodeModel | None:
        if not nodes:
            return None
        return sorted(nodes, key=lambda n: (n.current_jobs, -n.cpu_cores))[0]

    def round_robin(self, nodes: list[NodeModel]) -> NodeModel | None:
        if not nodes:
            return None
        with self._rr_lock:
            node_ids = [n.node_id for n in nodes]
            if self._round_robin_cycle is None:
                self._round_robin_cycle = cycle(node_ids)
            for _ in range(len(node_ids)):
                next_id = next(self._round_robin_cycle)
                match = next((n for n in nodes if n.node_id == next_id), None)
                if match:
                    return match
            self._round_robin_cycle = cycle(node_ids)
            return next((n for n in nodes), None)

    @staticmethod
    def least_loaded(nodes: list[NodeModel]) -> NodeModel | None:
        if not nodes:
            return None
        return min(nodes, key=lambda n: (n.current_jobs, -n.cpu_cores, -n.memory_mb))

    def select_node(self, algorithm: str, nodes: list[NodeModel]) -> NodeModel | None:
        normalized = algorithm.lower().strip()
        if normalized == "fcfs":
            return self.first_come_first_serve(nodes)
        if normalized == "priority":
            return self.priority_scheduling(nodes)
        if normalized == "round_robin":
            return self.round_robin(nodes)
        return self.least_loaded(nodes)
