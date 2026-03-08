"""Job execution primitives for simulated HPC workloads."""

from __future__ import annotations

import math
import random
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd


class JobExecutor:
    """Executes synthetic tasks to emulate CPU-heavy jobs."""

    def __init__(self) -> None:
        self._pool = ThreadPoolExecutor(max_workers=4)

    async def execute(self, task_type: str, execution_time: float) -> dict[str, float | int | str]:
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(
            self._pool,
            self._run_task,
            task_type,
            execution_time,
        )

    def _run_task(self, task_type: str, execution_time: float) -> dict[str, float | int | str]:
        started = time.perf_counter()
        task = task_type.lower().strip()

        if task == "compute_pi":
            samples = max(10_000, int(execution_time * 20_000))
            inside = sum(1 for _ in range(samples) if (random.random() ** 2 + random.random() ** 2) <= 1)
            pi_estimate = 4 * inside / samples
            result: dict[str, float | int | str] = {"pi_estimate": pi_estimate, "samples": samples}
        elif task == "matrix_multiplication":
            n = max(64, int(execution_time * 32))
            a = np.random.rand(n, n)
            b = np.random.rand(n, n)
            c = a @ b
            result = {"shape": f"{n}x{n}", "checksum": float(np.sum(c))}
        elif task == "monte_carlo_simulation":
            sims = max(1000, int(execution_time * 10000))
            values = np.random.normal(loc=0.0, scale=1.0, size=sims)
            result = {"mean": float(np.mean(values)), "std": float(np.std(values)), "samples": sims}
        elif task == "data_processing":
            rows = max(1000, int(execution_time * 2000))
            df = pd.DataFrame({"x": np.random.randint(1, 100, size=rows), "y": np.random.random(size=rows)})
            grouped = df.groupby("x")["y"].mean()
            result = {"rows": rows, "groups": int(grouped.shape[0]), "mean": float(grouped.mean())}
        else:
            time.sleep(max(0.1, execution_time))
            result = {"message": f"completed generic task {task_type}"}

        elapsed = time.perf_counter() - started
        result["elapsed"] = elapsed
        result["cpu_hint"] = math.ceil(elapsed)
        return result
