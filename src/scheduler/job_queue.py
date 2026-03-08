"""Redis-backed queue abstraction for job lifecycle management."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass

import redis
from redis.exceptions import RedisError

from src.utils.config import settings

logger = logging.getLogger(__name__)

PENDING_QUEUE = "pending_jobs"
RUNNING_QUEUE = "running_jobs"
FAILED_QUEUE = "failed_jobs"
COMPLETED_QUEUE = "completed_jobs"


@dataclass(slots=True)
class QueueJob:
    """Serializable queue payload."""

    job_id: str
    priority: int
    required_cpu: int
    required_memory: int
    task_type: str
    execution_time: float


class JobQueue:
    """Handles queue operations with Redis and resilient error handling."""

    def __init__(self) -> None:
        self.client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

    def _serialize(self, job: QueueJob) -> str:
        return json.dumps(asdict(job))

    def _deserialize(self, payload: str) -> QueueJob:
        return QueueJob(**json.loads(payload))

    def enqueue_pending(self, job: QueueJob) -> None:
        try:
            self.client.zadd(PENDING_QUEUE, {self._serialize(job): max(1, job.priority)})
        except RedisError:
            logger.exception("Failed to enqueue pending job", extra={"job_id": job.job_id})

    def dequeue_pending(self) -> QueueJob | None:
        try:
            items = self.client.zpopmax(PENDING_QUEUE, count=1)
            if not items:
                return None
            payload = items[0][0]
            return self._deserialize(payload)
        except RedisError:
            logger.exception("Failed to dequeue pending job")
            return None

    def push_running(self, job_id: str) -> None:
        try:
            self.client.sadd(RUNNING_QUEUE, job_id)
        except RedisError:
            logger.exception("Failed to mark job running", extra={"job_id": job_id})

    def move_to_completed(self, job_id: str) -> None:
        try:
            self.client.srem(RUNNING_QUEUE, job_id)
            self.client.sadd(COMPLETED_QUEUE, job_id)
        except RedisError:
            logger.exception("Failed to mark job completed", extra={"job_id": job_id})

    def move_to_failed(self, job_id: str) -> None:
        try:
            self.client.srem(RUNNING_QUEUE, job_id)
            self.client.sadd(FAILED_QUEUE, job_id)
        except RedisError:
            logger.exception("Failed to mark job failed", extra={"job_id": job_id})

    def remove_running(self, job_id: str) -> None:
        try:
            self.client.srem(RUNNING_QUEUE, job_id)
        except RedisError:
            logger.exception("Failed to remove running job", extra={"job_id": job_id})

    def pending_size(self) -> int:
        try:
            return int(self.client.zcard(PENDING_QUEUE))
        except RedisError:
            return 0

    def running_size(self) -> int:
        try:
            return int(self.client.scard(RUNNING_QUEUE))
        except RedisError:
            return 0

    def completed_size(self) -> int:
        try:
            return int(self.client.scard(COMPLETED_QUEUE))
        except RedisError:
            return 0

    def failed_size(self) -> int:
        try:
            return int(self.client.scard(FAILED_QUEUE))
        except RedisError:
            return 0

    def publish_assignment(self, node_id: str, job_id: str) -> None:
        key = f"node:{node_id}:jobs"
        try:
            self.client.rpush(key, job_id)
        except RedisError:
            logger.exception("Failed to publish assignment", extra={"job_id": job_id, "node_id": node_id})

    def consume_assignment(self, node_id: str) -> str | None:
        key = f"node:{node_id}:jobs"
        try:
            payload = self.client.lpop(key)
            return payload
        except RedisError:
            logger.exception("Failed to consume assignment", extra={"node_id": node_id})
            return None
