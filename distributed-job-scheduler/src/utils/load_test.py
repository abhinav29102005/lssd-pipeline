"""Simple load generator for performance simulation."""

from __future__ import annotations

import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib import request

API_BASE = "http://localhost:8000"


def submit_job(i: int) -> str:
    payload = {
        "task_type": "compute_pi" if i % 2 == 0 else "monte_carlo_simulation",
        "required_cpu": 1,
        "required_memory": 512,
        "priority": 1 + (i % 20),
        "execution_time": 2 + (i % 3),
    }
    req = request.Request(
        f"{API_BASE}/submit_job",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=10) as resp:  # noqa: S310
        body = json.loads(resp.read().decode("utf-8"))
        return body["job_id"]


def get_job(job_id: str) -> dict:
    with request.urlopen(f"{API_BASE}/job/{job_id}", timeout=10) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def run_load(total_jobs: int = 1000, workers: int = 50) -> None:
    started = time.time()
    job_ids: list[str] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(submit_job, i) for i in range(total_jobs)]
        for f in as_completed(futures):
            job_ids.append(f.result())

    submit_elapsed = time.time() - started
    print(f"Submitted {len(job_ids)} jobs in {submit_elapsed:.2f}s")

    wait_times: list[float] = []
    completed = set()

    while len(completed) < len(job_ids):
        for job_id in job_ids:
            if job_id in completed:
                continue
            data = get_job(job_id)
            if data["status"] in {"completed", "failed", "cancelled"}:
                completed.add(job_id)
                if data.get("submission_time") and data.get("completion_time"):
                    s = datetime.fromisoformat(data["submission_time"])
                    c = datetime.fromisoformat(data["completion_time"])
                    wait_times.append((c - s).total_seconds())
        print(f"Completed: {len(completed)}/{len(job_ids)}")
        time.sleep(1)

    if wait_times:
        print(f"Average end-to-end time: {statistics.mean(wait_times):.2f}s")
        print(f"P95 end-to-end time: {statistics.quantiles(wait_times, n=100)[94]:.2f}s")


if __name__ == "__main__":
    run_load()
