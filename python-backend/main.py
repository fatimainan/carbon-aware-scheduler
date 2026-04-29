"""
python-backend/main.py
────────────────────────────────────────────────────────────────────────────────
FastAPI service that exposes the Carbon-Aware Scheduler's execution log
to the React dashboard.

Drop this file into your `carbon_aware_scheduler` project (or any path that
can `import` your existing code). It does NOT replace your scheduler — it
runs alongside `main.py` / `worker.py` and reads the same log files they
write to (`logs/execution_log.json` by default).

Endpoints
─────────
    GET  /api/dashboard   → { config, cycles, generatedAt }
    GET  /api/healthz     → { status: "ok" }

Run
───
    pip install fastapi "uvicorn[standard]"
    uvicorn python-backend.main:app --reload --host 0.0.0.0 --port 8000

Then in the dashboard:
    VITE_API_BASE_URL=http://localhost:8000
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Config (mirror your scheduler's config.py) ────────────────────────────────
LOG_FILE_JSON = os.getenv("LOG_FILE_JSON", "logs/execution_log.json")
THRESHOLD = float(os.getenv("CARBON_THRESHOLD", "200"))
DELAY_SECONDS = int(os.getenv("DELAY_SECONDS", "30"))
ZONE = os.getenv("CARBON_ZONE", "DE")
ACTION_NAME = os.getenv("ACTION_NAME", "data_processor")

# Comma-separated list of allowed origins for CORS.
# Set this to your dashboard URL in production, e.g.
#   ALLOWED_ORIGINS="https://carbon-dashboard.replit.app"
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")
    if o.strip()
]

# ── Models (must match the React `DashboardPayload` type) ─────────────────────


class CycleResult(BaseModel):
    cycle: int
    timestampOffsetMin: float
    carbonIntensity: float
    decision: Literal["execute", "delay"]
    executionStatus: Literal["executed", "delayed", "queued"]
    executionDurationMs: float | None
    scenario: Literal["A", "B"]


class RunConfig(BaseModel):
    threshold: float
    delaySeconds: int
    zone: str
    actionName: str


class DashboardPayload(BaseModel):
    config: RunConfig
    cycles: list[CycleResult]
    generatedAt: str


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Carbon-Aware Scheduler API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _read_log_records() -> list[dict]:
    """Read the newline-delimited JSON log written by executor.Executor."""
    path = Path(LOG_FILE_JSON)
    if not path.exists():
        return []

    records: list[dict] = []
    with path.open("r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _to_cycles(records: list[dict]) -> list[CycleResult]:
    """Map raw log records → the dashboard's CycleResult shape."""
    if not records:
        return []

    # Anchor the time-offset axis to the first record's timestamp so the
    # x-axis always starts at T+0 minutes.
    anchor = _parse_ts(records[0]["timestamp"])

    cycles: list[CycleResult] = []
    for idx, rec in enumerate(records, start=1):
        ts = _parse_ts(rec["timestamp"])
        offset_min = (ts - anchor).total_seconds() / 60.0

        decision = rec.get("decision", "execute")
        status = rec.get("execution_status") or (
            "executed" if decision == "execute" else "delayed"
        )
        duration = rec.get("duration_ms")
        if duration in ("", None):
            duration = None
        else:
            try:
                duration = float(duration)
            except (TypeError, ValueError):
                duration = None

        carbon = float(rec.get("carbon_intensity", 0.0))
        threshold = float(rec.get("threshold", THRESHOLD))

        cycles.append(
            CycleResult(
                cycle=idx,
                timestampOffsetMin=round(offset_min, 2),
                carbonIntensity=carbon,
                decision="execute" if decision == "execute" else "delay",
                executionStatus=status if status in ("executed", "delayed", "queued")
                else ("executed" if decision == "execute" else "delayed"),
                executionDurationMs=duration,
                scenario="A" if carbon <= threshold else "B",
            )
        )
    return cycles


def _parse_ts(raw: str) -> datetime:
    # Handles both `2026-04-19T19:10:09.972980+00:00` and `...Z` forms.
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw)


# ── Routes ────────────────────────────────────────────────────────────────────


@app.get("/api/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/api/dashboard", response_model=DashboardPayload)
def get_dashboard() -> DashboardPayload:
    records = _read_log_records()
    cycles = _to_cycles(records)
    return DashboardPayload(
        config=RunConfig(
            threshold=THRESHOLD,
            delaySeconds=DELAY_SECONDS,
            zone=ZONE,
            actionName=ACTION_NAME,
        ),
        cycles=cycles,
        generatedAt=datetime.now(timezone.utc).isoformat(),
    )
