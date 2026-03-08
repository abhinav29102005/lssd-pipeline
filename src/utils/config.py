"""Configuration helpers for the distributed scheduler."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class Settings:
    """Application settings loaded from environment variables."""

    app_name: str = os.getenv("APP_NAME", "lssd-pipeline")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    postgres_dsn: str = os.getenv(
        "POSTGRES_DSN",
        "postgresql+psycopg2://scheduler:scheduler@postgres:5432/scheduler_db",
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

    scheduler_algorithm: str = os.getenv("SCHEDULER_ALGORITHM", "least_loaded")
    schedule_interval_seconds: float = float(os.getenv("SCHEDULE_INTERVAL_SECONDS", "0.2"))

    cluster_size: int = int(os.getenv("CLUSTER_SIZE", "100"))
    simulate_nodes: bool = os.getenv("SIMULATE_NODES", "true").lower() == "true"

    default_node_cpu: int = int(os.getenv("DEFAULT_NODE_CPU", "8"))
    default_node_memory_mb: int = int(os.getenv("DEFAULT_NODE_MEMORY_MB", "32768"))

    heartbeat_interval: float = float(os.getenv("HEARTBEAT_INTERVAL", "2"))
    heartbeat_timeout: float = float(os.getenv("HEARTBEAT_TIMEOUT", "8"))

    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    base_retry_delay: float = float(os.getenv("BASE_RETRY_DELAY", "1.5"))
    job_timeout: float = float(os.getenv("JOB_TIMEOUT", "120"))

    worker_poll_interval: float = float(os.getenv("WORKER_POLL_INTERVAL", "0.5"))
    failure_rate: float = float(os.getenv("JOB_FAILURE_RATE", "0.07"))


settings = Settings()
