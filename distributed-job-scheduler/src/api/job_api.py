"""FastAPI service for job submission, cluster monitoring, and management."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select

from src.cluster.node_manager import NodeManager
from src.database.db import get_db_session, init_db
from src.database.models import ClusterMetricModel, JobModel, JobStatus, NodeModel
from src.scheduler.job_queue import JobQueue, QueueJob
from src.utils.config import settings

app = FastAPI(
    title="Distributed Job Scheduler API",
    version="2.0.0",
    description="Production-grade API for managing distributed job scheduling across 100+ compute nodes.",
)

# Allow dashboard and other frontends to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

queue = JobQueue()
node_manager = NodeManager()


# ────────────────────── request / response models ──────────────────────────
class SubmitJobRequest(BaseModel):
    task_type: str = Field(default="compute_pi")
    required_cpu: int = Field(default=1, ge=1)
    required_memory: int = Field(default=512, ge=128)
    priority: int = Field(default=1, ge=1, le=100)
    execution_time: float = Field(default=3.0, ge=0.1, le=600)


class BatchSubmitRequest(BaseModel):
    """Submit multiple jobs in one call."""
    jobs: list[SubmitJobRequest]


# ────────────────────── lifecycle hooks ────────────────────────────────────
@app.on_event("startup")
def on_startup() -> None:
    init_db()


# ────────────────────── job endpoints ─────────────────────────────────────
@app.post("/submit_job", tags=["Jobs"])
def submit_job(payload: SubmitJobRequest) -> dict[str, str]:
    """Submit a single job to the scheduling queue."""
    with get_db_session() as session:
        job = JobModel(
            job_id=uuid.uuid4(),
            task_type=payload.task_type,
            required_cpu=payload.required_cpu,
            required_memory=payload.required_memory,
            priority=payload.priority,
            execution_time=payload.execution_time,
            retry_count=0,
            max_retries=settings.max_retries,
            status=JobStatus.PENDING,
            submission_time=datetime.utcnow(),
        )
        session.add(job)
        session.flush()

        queue.enqueue_pending(
            QueueJob(
                job_id=str(job.job_id),
                priority=job.priority,
                required_cpu=job.required_cpu,
                required_memory=job.required_memory,
                task_type=job.task_type,
                execution_time=job.execution_time,
            )
        )

        return {"job_id": str(job.job_id), "status": "queued"}


@app.post("/submit_jobs", tags=["Jobs"])
def submit_jobs_batch(payload: BatchSubmitRequest) -> dict[str, list[str] | int]:
    """Submit multiple jobs in a single batch request."""
    job_ids: list[str] = []
    with get_db_session() as session:
        for item in payload.jobs:
            job = JobModel(
                job_id=uuid.uuid4(),
                task_type=item.task_type,
                required_cpu=item.required_cpu,
                required_memory=item.required_memory,
                priority=item.priority,
                execution_time=item.execution_time,
                retry_count=0,
                max_retries=settings.max_retries,
                status=JobStatus.PENDING,
                submission_time=datetime.utcnow(),
            )
            session.add(job)
            session.flush()
            queue.enqueue_pending(
                QueueJob(
                    job_id=str(job.job_id),
                    priority=job.priority,
                    required_cpu=job.required_cpu,
                    required_memory=job.required_memory,
                    task_type=job.task_type,
                    execution_time=job.execution_time,
                )
            )
            job_ids.append(str(job.job_id))
    return {"job_ids": job_ids, "count": len(job_ids)}


@app.get("/job/{job_id}", tags=["Jobs"])
def get_job(job_id: str) -> dict[str, str | int | float | None]:
    """Get detailed status for a single job."""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid job_id") from exc

    with get_db_session() as session:
        job = session.get(JobModel, job_uuid)
        if not job:
            raise HTTPException(status_code=404, detail="job not found")

        return {
            "job_id": str(job.job_id),
            "task_type": job.task_type,
            "status": job.status.value,
            "priority": job.priority,
            "required_cpu": job.required_cpu,
            "required_memory": job.required_memory,
            "retry_count": job.retry_count,
            "node_assigned": job.node_assigned,
            "error_message": job.error_message,
            "submission_time": job.submission_time.isoformat() if job.submission_time else None,
            "start_time": job.start_time.isoformat() if job.start_time else None,
            "completion_time": job.completion_time.isoformat() if job.completion_time else None,
        }


@app.get("/jobs", tags=["Jobs"])
def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status (pending, running, completed, failed)"),
    task_type: Optional[str] = Query(None, description="Filter by task_type"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict[str, list[dict] | int]:
    """List jobs with optional filters and pagination."""
    with get_db_session() as session:
        stmt = select(JobModel)
        if status:
            try:
                stmt = stmt.where(JobModel.status == JobStatus(status.lower()))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        if task_type:
            stmt = stmt.where(JobModel.task_type == task_type)
        stmt = stmt.order_by(desc(JobModel.submission_time)).offset(offset).limit(limit)
        jobs = session.execute(stmt).scalars().all()
        total = session.scalar(select(func.count()).select_from(JobModel)) or 0
        return {
            "total": int(total),
            "jobs": [
                {
                    "job_id": str(j.job_id),
                    "task_type": j.task_type,
                    "status": j.status.value,
                    "priority": j.priority,
                    "retry_count": j.retry_count,
                    "node_assigned": j.node_assigned,
                    "submission_time": j.submission_time.isoformat() if j.submission_time else None,
                }
                for j in jobs
            ],
        }


@app.delete("/job/{job_id}", tags=["Jobs"])
def cancel_job(job_id: str) -> dict[str, str]:
    """Cancel a pending or running job."""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid job_id") from exc

    with get_db_session() as session:
        job = session.get(JobModel, job_uuid)
        if not job:
            raise HTTPException(status_code=404, detail="job not found")
        if job.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
            return {"job_id": job_id, "status": job.status.value}

        job.status = JobStatus.CANCELLED
        queue.remove_running(job_id)
        return {"job_id": job_id, "status": "cancelled"}


# ────────────────────── cluster endpoints ─────────────────────────────────
@app.get("/cluster_status", tags=["Cluster"])
def cluster_status() -> dict[str, float | int]:
    """Live cluster summary."""
    counts = node_manager.cluster_counts()
    with get_db_session() as session:
        running_jobs = (
            session.scalar(select(func.count()).select_from(JobModel).where(JobModel.status == JobStatus.RUNNING))
            or 0
        )
        completed_jobs = (
            session.scalar(select(func.count()).select_from(JobModel).where(JobModel.status == JobStatus.COMPLETED))
            or 0
        )

    return {
        "total_nodes": counts["total_nodes"],
        "active_nodes": counts["active_nodes"],
        "failed_nodes": counts["failed_nodes"],
        "running_jobs": int(running_jobs),
        "completed_jobs": int(completed_jobs),
        "queue_size": queue.pending_size(),
        "cluster_utilization": round(
            int(running_jobs) / max(1, counts["total_nodes"]),
            4,
        ),
    }


@app.get("/nodes", tags=["Cluster"])
def list_nodes(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(200, ge=1, le=1000),
) -> dict[str, list[dict] | int]:
    """List all registered compute nodes."""
    with get_db_session() as session:
        stmt = select(NodeModel)
        if status:
            from src.database.models import NodeStatus as NS
            try:
                stmt = stmt.where(NodeModel.status == NS(status.lower()))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid node status: {status}")
        stmt = stmt.order_by(NodeModel.node_id).limit(limit)
        nodes = session.execute(stmt).scalars().all()
        total = session.scalar(select(func.count()).select_from(NodeModel)) or 0
        return {
            "total": int(total),
            "nodes": [
                {
                    "node_id": n.node_id,
                    "cpu_cores": n.cpu_cores,
                    "memory_mb": n.memory_mb,
                    "status": n.status.value,
                    "current_jobs": n.current_jobs,
                    "last_heartbeat": n.last_heartbeat.isoformat() if n.last_heartbeat else None,
                }
                for n in nodes
            ],
        }


@app.get("/metrics", tags=["Monitoring"])
def get_metrics(
    limit: int = Query(200, ge=1, le=1000),
) -> dict[str, list[dict] | int]:
    """Retrieve cluster metric history."""
    with get_db_session() as session:
        stmt = (
            select(ClusterMetricModel)
            .order_by(desc(ClusterMetricModel.timestamp))
            .limit(limit)
        )
        rows = session.execute(stmt).scalars().all()
        return {
            "count": len(rows),
            "metrics": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "total_nodes": m.total_nodes,
                    "active_nodes": m.active_nodes,
                    "failed_nodes": m.failed_nodes,
                    "running_jobs": m.running_jobs,
                    "completed_jobs": m.completed_jobs,
                    "queue_size": m.queue_size,
                    "cluster_utilization": m.cluster_utilization,
                }
                for m in rows
            ],
        }


@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    """Simple liveness probe."""
    return {"status": "healthy", "algorithm": settings.scheduler_algorithm, "version": "2.0.0"}
