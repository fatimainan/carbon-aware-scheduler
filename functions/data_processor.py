"""
functions/data_processor.py
────────────────────────────────────────────────────────────────────────────────
Sample OpenWhisk Action — "data_processor"

This is the serverless function that the carbon-aware scheduler decides
whether to execute or delay.  It simulates a batch data-processing workload
that has meaningful but deferrable compute requirements.

OpenWhisk Action Contract
-------------------------
* Function must be named `main(params: dict) -> dict`
* Return value is JSON-serialisable dict
* Errors: raise Exception or return {"error": "..."}

Deployment
----------
    wsk action create data_processor functions/data_processor.py \
        --kind python:3

Invocation (via wsk CLI)
----------
    wsk action invoke data_processor --result \
        --param task_name "batch-etl-001" \
        --param payload_size 1024
"""

from __future__ import annotations

import hashlib
import math
import time
from datetime import datetime, timezone


# ── OpenWhisk entry point ─────────────────────────────────────────────────────

def main(params: dict) -> dict:
    """
    OpenWhisk Action entry point.

    Accepted params
    ---------------
    task_name    : str   label for this job (default: "default-task")
    payload_size : int   synthetic workload size in "units" (default: 512)

    Returns
    -------
    dict with:
        status       : "success" | "error"
        task_name    : str
        result       : computed checksum (proof of work)
        duration_ms  : wall-clock execution time
        executed_at  : ISO-8601 UTC timestamp
    """
    start = time.perf_counter()

    task_name    = params.get("task_name",    "default-task")
    payload_size = int(params.get("payload_size", 512))

    try:
        # ── Simulate a real workload ──────────────────────────────────────────
        # We compute a checksum over synthetic data as proof the function ran.
        data    = _generate_payload(payload_size)
        checksum = _compute_checksum(data)
        stats   = _compute_stats(data)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        result = {
            "status":      "success",
            "task_name":   task_name,
            "payload_size": payload_size,
            "checksum":    checksum,
            "stats":       stats,
            "duration_ms": duration_ms,
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }
        return result

    except Exception as exc:                      # noqa: BLE001
        return {
            "status":     "error",
            "task_name":  task_name,
            "error":      str(exc),
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }


# ── Private helpers ───────────────────────────────────────────────────────────

def _generate_payload(size: int) -> list[float]:
    """Generate a deterministic list of floats (synthetic dataset)."""
    return [math.sin(i * 0.01) * math.cos(i * 0.03) for i in range(size)]


def _compute_checksum(data: list[float]) -> str:
    """SHA-256 of the string-serialised data."""
    raw = ",".join(f"{v:.6f}" for v in data)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _compute_stats(data: list[float]) -> dict:
    """Minimal descriptive statistics over the payload."""
    n   = len(data)
    avg = sum(data) / n
    mn  = min(data)
    mx  = max(data)
    variance = sum((x - avg) ** 2 for x in data) / n
    return {
        "count":    n,
        "mean":     round(avg, 6),
        "min":      round(mn, 6),
        "max":      round(mx, 6),
        "std_dev":  round(variance ** 0.5, 6),
    }


# ── Local testing (not used by OpenWhisk) ─────────────────────────────────────
if __name__ == "__main__":
    test_params = {"task_name": "local-test", "payload_size": 256}
    output = main(test_params)
    print(output)
