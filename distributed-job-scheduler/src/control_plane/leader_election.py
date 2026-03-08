"""Leader election abstraction built on top of the Raft consensus layer.

Provides a high-level API for the scheduler to check leadership status
and receive notifications when leadership changes.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from src.control_plane.raft_consensus import RaftNode, RaftState

logger = logging.getLogger(__name__)


class LeaderElection:
    """High-level leader election manager wrapping a Raft consensus cluster.

    Instantiates ``cluster_size`` Raft nodes in-process, runs their event
    loops, and exposes convenience methods for the scheduler to query
    leadership and subscribe to changes.

    Parameters
    ----------
    cluster_size:
        Total number of consensus nodes (should be odd for majority).
    on_leader_change:
        Optional ``(leader_id: str | None) -> None`` callback.
    """

    def __init__(
        self,
        cluster_size: int = 3,
        on_leader_change: Callable[[str | None], None] | None = None,
    ) -> None:
        self.cluster_size = max(3, cluster_size | 1)  # force odd, min 3
        self._on_leader_change = on_leader_change
        self._current_leader: str | None = None
        self._running = False

        # Build node IDs
        self._node_ids = [f"raft-{i}" for i in range(self.cluster_size)]
        self._nodes: dict[str, RaftNode] = {}

        self._init_nodes()

    # ── internal setup ───────────────────────────────────────────────────

    def _init_nodes(self) -> None:
        """Create and cross-register all Raft nodes."""
        for nid in self._node_ids:
            peers = [p for p in self._node_ids if p != nid]
            self._nodes[nid] = RaftNode(
                node_id=nid,
                peers=peers,
                on_leader_change=self._handle_leader_change,
                election_timeout_range=(150, 300),
                heartbeat_interval=0.1,
            )
        # Wire peers for in-process RPC
        for node in self._nodes.values():
            node.register_peers(self._nodes)

    def _handle_leader_change(self, leader_id: str | None) -> None:
        if leader_id == self._current_leader:
            return
        prev = self._current_leader
        self._current_leader = leader_id
        logger.info(
            "Leader changed",
            extra={"prev_leader": prev, "new_leader": leader_id},
        )
        if self._on_leader_change:
            self._on_leader_change(leader_id)

    # ── public API ───────────────────────────────────────────────────────

    def is_leader(self, node_id: str | None = None) -> bool:
        """Check whether a given node (default: any) is the current leader."""
        if node_id:
            node = self._nodes.get(node_id)
            return node is not None and node.state == RaftState.LEADER
        return self._current_leader is not None

    @property
    def current_leader(self) -> str | None:
        """Return the current leader ID or ``None``."""
        return self._current_leader

    def leader_node(self) -> RaftNode | None:
        """Return the ``RaftNode`` instance that is currently LEADER."""
        if self._current_leader:
            return self._nodes.get(self._current_leader)
        return None

    def cluster_status(self) -> list[dict[str, Any]]:
        """Return status snapshot of all consensus nodes."""
        return [node.status() for node in self._nodes.values()]

    def propose(self, command: str, data: dict[str, Any] | None = None) -> bool:
        """Propose a command to the leader's log.

        Returns ``True`` if the entry was appended (leader available),
        ``False`` otherwise.
        """
        leader = self.leader_node()
        if leader is None:
            logger.warning("No leader available to accept proposal", extra={"command": command})
            return False
        entry = leader.leader_append(command, data)
        return entry is not None

    # ── lifecycle ────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start all Raft node event loops concurrently."""
        self._running = True
        tasks = [asyncio.create_task(node.run(), name=f"raft-{nid}") for nid, node in self._nodes.items()]
        logger.info("Leader election started", extra={"cluster_size": self.cluster_size})
        await asyncio.gather(*tasks)

    def stop(self) -> None:
        """Stop all Raft nodes."""
        self._running = False
        for node in self._nodes.values():
            node.stop()
        logger.info("Leader election stopped")
