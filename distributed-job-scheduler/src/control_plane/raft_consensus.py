"""Simplified Raft consensus implementation for distributed scheduler coordination.

Implements core Raft protocol mechanics:
- Leader election with randomized timeouts
- Log replication via AppendEntries RPCs
- Term-based consistency and vote tracking
- State machine callbacks for cluster state changes

This is a *single-process simulation* of the Raft protocol suitable for
demonstrating distributed consensus concepts. In production, each RaftNode
would run on a separate machine and communicate over the network.
"""

from __future__ import annotations

import asyncio
import enum
import hashlib
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ──────────────────────────── data types ─────────────────────────────────────


class RaftState(str, enum.Enum):
    """Possible roles for a Raft node."""

    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


@dataclass(slots=True)
class LogEntry:
    """Single entry in the Raft replicated log."""

    term: int
    index: int
    command: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def fingerprint(self) -> str:
        """Deterministic hash for integrity checks."""
        raw = f"{self.term}:{self.index}:{self.command}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]


@dataclass(slots=True)
class RequestVoteArgs:
    """RequestVote RPC arguments."""

    term: int
    candidate_id: str
    last_log_index: int
    last_log_term: int


@dataclass(slots=True)
class RequestVoteReply:
    """RequestVote RPC reply."""

    term: int
    vote_granted: bool


@dataclass(slots=True)
class AppendEntriesArgs:
    """AppendEntries RPC arguments (heartbeat or log replication)."""

    term: int
    leader_id: str
    prev_log_index: int
    prev_log_term: int
    entries: list[LogEntry]
    leader_commit: int


@dataclass(slots=True)
class AppendEntriesReply:
    """AppendEntries RPC reply."""

    term: int
    success: bool
    match_index: int


# ──────────────────────────── Raft node ──────────────────────────────────────


class RaftNode:
    """Core Raft consensus node implementing the state machine.

    Parameters
    ----------
    node_id:
        Unique identifier for this node within the consensus cluster.
    peers:
        List of peer node IDs that participate in the cluster.
    on_leader_change:
        Optional callback ``(leader_id: str | None) -> None`` invoked
        whenever the leadership changes.
    election_timeout_range:
        ``(min_ms, max_ms)`` tuple for randomised election timeouts.
    heartbeat_interval:
        Seconds between leader heartbeats.
    """

    def __init__(
        self,
        node_id: str,
        peers: list[str],
        on_leader_change: Callable[[str | None], None] | None = None,
        election_timeout_range: tuple[int, int] = (150, 300),
        heartbeat_interval: float = 0.1,
    ) -> None:
        self.node_id = node_id
        self.peers = peers
        self._on_leader_change = on_leader_change
        self._election_timeout_range = election_timeout_range
        self._heartbeat_interval = heartbeat_interval

        # Persistent state (would be on stable storage in production)
        self.current_term: int = 0
        self.voted_for: str | None = None
        self.log: list[LogEntry] = []

        # Volatile state
        self.state: RaftState = RaftState.FOLLOWER
        self.leader_id: str | None = None
        self.commit_index: int = -1
        self.last_applied: int = -1

        # Leader-only volatile state
        self.next_index: dict[str, int] = {}
        self.match_index: dict[str, int] = {}

        # Timing
        self._last_heartbeat = time.time()
        self._election_timeout = self._random_timeout()
        self._votes_received: set[str] = set()
        self._running = False

        # Peer node references (for in-process simulation)
        self._peer_nodes: dict[str, RaftNode] = {}

        # Applied state machine (stores committed commands)
        self.state_machine: list[dict[str, Any]] = []

        logger.info(
            "RaftNode initialised",
            extra={"node_id": node_id, "peers": peers},
        )

    # ── helpers ──────────────────────────────────────────────────────────

    def _random_timeout(self) -> float:
        lo, hi = self._election_timeout_range
        return random.randint(lo, hi) / 1000.0

    def _reset_election_timer(self) -> None:
        self._last_heartbeat = time.time()
        self._election_timeout = self._random_timeout()

    def _last_log_index(self) -> int:
        return len(self.log) - 1

    def _last_log_term(self) -> int:
        return self.log[-1].term if self.log else 0

    def _become_follower(self, term: int) -> None:
        prev = self.state
        self.state = RaftState.FOLLOWER
        self.current_term = term
        self.voted_for = None
        self._votes_received.clear()
        if prev != RaftState.FOLLOWER:
            logger.info("Became FOLLOWER", extra={"node_id": self.node_id, "term": term})

    def _become_candidate(self) -> None:
        self.state = RaftState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self._votes_received = {self.node_id}
        self._reset_election_timer()
        logger.info(
            "Became CANDIDATE, starting election",
            extra={"node_id": self.node_id, "term": self.current_term},
        )

    def _become_leader(self) -> None:
        self.state = RaftState.LEADER
        self.leader_id = self.node_id
        # Initialise leader volatile state
        last = self._last_log_index()
        for peer in self.peers:
            self.next_index[peer] = last + 1
            self.match_index[peer] = -1
        logger.info(
            "Became LEADER",
            extra={"node_id": self.node_id, "term": self.current_term},
        )
        if self._on_leader_change:
            self._on_leader_change(self.node_id)

    # ── peer wiring (in-process simulation) ──────────────────────────────

    def register_peers(self, peer_nodes: dict[str, "RaftNode"]) -> None:
        """Register peer RaftNode instances for in-process RPC simulation."""
        self._peer_nodes = {k: v for k, v in peer_nodes.items() if k != self.node_id}

    # ── RequestVote RPC ──────────────────────────────────────────────────

    def handle_request_vote(self, args: RequestVoteArgs) -> RequestVoteReply:
        """Process an incoming RequestVote RPC."""
        if args.term < self.current_term:
            return RequestVoteReply(term=self.current_term, vote_granted=False)

        if args.term > self.current_term:
            self._become_follower(args.term)

        # Grant vote if we haven't voted yet or already voted for this candidate
        log_ok = (args.last_log_term > self._last_log_term()) or (
            args.last_log_term == self._last_log_term()
            and args.last_log_index >= self._last_log_index()
        )

        if (self.voted_for is None or self.voted_for == args.candidate_id) and log_ok:
            self.voted_for = args.candidate_id
            self._reset_election_timer()
            logger.debug(
                "Granted vote",
                extra={"node_id": self.node_id, "voted_for": args.candidate_id, "term": args.term},
            )
            return RequestVoteReply(term=self.current_term, vote_granted=True)

        return RequestVoteReply(term=self.current_term, vote_granted=False)

    # ── AppendEntries RPC ────────────────────────────────────────────────

    def handle_append_entries(self, args: AppendEntriesArgs) -> AppendEntriesReply:
        """Process an incoming AppendEntries RPC (heartbeat or log replication)."""
        if args.term < self.current_term:
            return AppendEntriesReply(term=self.current_term, success=False, match_index=-1)

        self._reset_election_timer()

        if args.term > self.current_term or self.state != RaftState.FOLLOWER:
            self._become_follower(args.term)

        self.leader_id = args.leader_id

        # Log consistency check
        if args.prev_log_index >= 0:
            if args.prev_log_index >= len(self.log):
                return AppendEntriesReply(term=self.current_term, success=False, match_index=len(self.log) - 1)
            if self.log[args.prev_log_index].term != args.prev_log_term:
                self.log = self.log[: args.prev_log_index]
                return AppendEntriesReply(term=self.current_term, success=False, match_index=len(self.log) - 1)

        # Append new entries
        for entry in args.entries:
            if entry.index < len(self.log):
                if self.log[entry.index].term != entry.term:
                    self.log = self.log[: entry.index]
                    self.log.append(entry)
            else:
                self.log.append(entry)

        # Update commit index
        if args.leader_commit > self.commit_index:
            self.commit_index = min(args.leader_commit, self._last_log_index())
            self._apply_committed()

        return AppendEntriesReply(
            term=self.current_term,
            success=True,
            match_index=self._last_log_index(),
        )

    # ── log application ──────────────────────────────────────────────────

    def _apply_committed(self) -> None:
        """Apply committed log entries to the state machine."""
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied]
            self.state_machine.append({"command": entry.command, "data": entry.data, "term": entry.term})
            logger.debug(
                "Applied log entry",
                extra={"node_id": self.node_id, "index": self.last_applied, "command": entry.command},
            )

    # ── leader: replicate + commit ───────────────────────────────────────

    def leader_append(self, command: str, data: dict[str, Any] | None = None) -> LogEntry | None:
        """Append a new entry to the leader's log for replication.

        Returns the ``LogEntry`` if this node is the current leader,
        otherwise ``None``.
        """
        if self.state != RaftState.LEADER:
            return None
        entry = LogEntry(
            term=self.current_term,
            index=len(self.log),
            command=command,
            data=data or {},
        )
        self.log.append(entry)
        logger.info("Leader appended log entry", extra={"node_id": self.node_id, "entry": command})
        return entry

    def _send_append_entries(self) -> None:
        """Send heartbeat / log entries to all peers (in-process)."""
        for peer_id, peer_node in self._peer_nodes.items():
            ni = self.next_index.get(peer_id, 0)
            prev_index = ni - 1
            prev_term = self.log[prev_index].term if 0 <= prev_index < len(self.log) else 0
            entries = self.log[ni:]

            args = AppendEntriesArgs(
                term=self.current_term,
                leader_id=self.node_id,
                prev_log_index=prev_index,
                prev_log_term=prev_term,
                entries=entries,
                leader_commit=self.commit_index,
            )

            reply = peer_node.handle_append_entries(args)
            if reply.term > self.current_term:
                self._become_follower(reply.term)
                return

            if reply.success:
                self.match_index[peer_id] = reply.match_index
                self.next_index[peer_id] = reply.match_index + 1
            else:
                self.next_index[peer_id] = max(0, self.next_index.get(peer_id, 1) - 1)

        # Advance commit index
        for n in range(self._last_log_index(), self.commit_index, -1):
            if n < len(self.log) and self.log[n].term == self.current_term:
                replicated = sum(1 for mi in self.match_index.values() if mi >= n)
                if replicated + 1 > (len(self.peers) + 1) // 2:
                    self.commit_index = n
                    self._apply_committed()
                    break

    def _send_request_votes(self) -> None:
        """Send RequestVote RPCs to all peers."""
        for peer_id, peer_node in self._peer_nodes.items():
            args = RequestVoteArgs(
                term=self.current_term,
                candidate_id=self.node_id,
                last_log_index=self._last_log_index(),
                last_log_term=self._last_log_term(),
            )
            reply = peer_node.handle_request_vote(args)
            if reply.term > self.current_term:
                self._become_follower(reply.term)
                return
            if reply.vote_granted:
                self._votes_received.add(peer_id)

        # Check if we have a majority
        majority = (len(self.peers) + 1) // 2 + 1
        if len(self._votes_received) >= majority:
            self._become_leader()

    # ── main tick loop ───────────────────────────────────────────────────

    async def run(self) -> None:
        """Run the Raft main loop (call as an ``asyncio.Task``)."""
        self._running = True
        logger.info("Raft node started", extra={"node_id": self.node_id})

        while self._running:
            elapsed = time.time() - self._last_heartbeat

            if self.state == RaftState.LEADER:
                if elapsed >= self._heartbeat_interval:
                    self._send_append_entries()
                    self._last_heartbeat = time.time()

            elif self.state in {RaftState.FOLLOWER, RaftState.CANDIDATE}:
                if elapsed >= self._election_timeout:
                    self._become_candidate()
                    self._send_request_votes()

            await asyncio.sleep(0.05)

    def stop(self) -> None:
        """Gracefully stop the Raft event loop."""
        self._running = False

    # ── diagnostics ──────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        """Return a snapshot of this node's Raft state."""
        return {
            "node_id": self.node_id,
            "state": self.state.value,
            "term": self.current_term,
            "leader_id": self.leader_id,
            "log_length": len(self.log),
            "commit_index": self.commit_index,
            "last_applied": self.last_applied,
            "voted_for": self.voted_for,
        }
