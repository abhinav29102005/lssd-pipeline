"""SQLAlchemy models for jobs, nodes, and cluster metrics."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base."""


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY_WAIT = "retry_wait"


class NodeStatus(str, enum.Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    FAILED = "failed"
    DRAINING = "draining"


class NodeModel(Base):
    """Represents a compute node in the cluster."""

    __tablename__ = "nodes"

    node_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    cpu_cores: Mapped[int] = mapped_column(Integer, nullable=False)
    memory_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[NodeStatus] = mapped_column(Enum(NodeStatus), nullable=False, default=NodeStatus.AVAILABLE)
    current_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)

    jobs: Mapped[list[JobModel]] = relationship(back_populates="node", cascade="all,delete")


class JobModel(Base):
    """Represents a scheduled or completed job."""

    __tablename__ = "jobs"

    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    required_cpu: Mapped[int] = mapped_column(Integer, nullable=False)
    required_memory: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    execution_time: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), nullable=False, default=JobStatus.PENDING)

    node_assigned: Mapped[str | None] = mapped_column(String(128), ForeignKey("nodes.node_id"), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(256), nullable=True)

    submission_time: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    completion_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    node: Mapped[NodeModel | None] = relationship(back_populates="jobs")


class ClusterMetricModel(Base):
    """Periodic cluster-level metrics for monitoring."""

    __tablename__ = "cluster_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)

    total_nodes: Mapped[int] = mapped_column(Integer, nullable=False)
    active_nodes: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_nodes: Mapped[int] = mapped_column(Integer, nullable=False)

    running_jobs: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_jobs: Mapped[int] = mapped_column(Integer, nullable=False)
    queue_size: Mapped[int] = mapped_column(Integer, nullable=False)
    cluster_utilization: Mapped[float] = mapped_column(Float, nullable=False)
