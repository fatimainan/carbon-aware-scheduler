"""
python-backend/main.py
────────────────────────────────────────────────────────────────────────────────
FastAPI service that exposes the Carbon-Aware Scheduler's execution logs
to the React dashboard.

CHANGES vs. original:
  - Added `?mode=sim|sandbox|live` query param to /api/dashboard
  - Each mode reads from a different JSON log file:
        sim     -> logs/execution_log_sim.json
        sandbox -> logs/execution_log_sandbox.json
        live    -> logs/execution_log_live.json
  - Falls back to LOG_FILE_JSON (old single-file behavior) if the
    mode-specific file doesn't exist, so nothing breaks if you haven't
    split your logs yet.

Run
───
    uvicorn python-backend.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Config ──────────────────────────────────────────────────────────────────
LOG_FILE_JSON = os.getenv("LOG_FILE_JSON", "logs/execution_log.json")
LOGS_DIR = Path(LOG_FILE_JSON).parent

MODE_FILES = {
    "sim":     LOGS_DIR / "execution_log_sim.json",
    "sandbox": LOGS_DIR / "execution_log_sandbox.json",
    "live":    LOGS_DIR / "execution_log_live.json",
}

THRESHOLD = float(os.getenv("CARBON_THRESHOLD", "350"))
DELAY_SECONDS = int(os.getenv("DELAY_SECONDS", "30"))
ZONE = os.getenv("CARBON_ZONE", "DE")
ACTION_NAME = os.getenv("ACTION_NAME", "data_processor")

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")
    if o.strip()
]

# ── Models ──────────────────────────────────────────────────────────────────


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

app = FastAPI(title="Carbon-Aware Scheduler API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _resolve_log_path(mode: str) -> Path:
    """Pick the JSON log file for the given mode, with fallback."""
    mode_path = MODE_FILES.get(mode)
    if mode_path and mode_path.exists():
        return mode_path

    # Fallback: old single-file behavior (useful during migration)
    fallback = Path(LOG_FILE_JSON)
    return fallback


def _read_log_records(path: Path) -> list[dict]:
    """Read the newline-delimited JSON log written by executor.Executor."""
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
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw)


def _config_from_records(records: list[dict]) -> RunConfig:
    """Use the most recent record's threshold/zone/action if available,
    otherwise fall back to env defaults."""
    threshold, zone, action = THRESHOLD, ZONE, ACTION_NAME
    if records:
        last = records[-1]
        threshold = float(last.get("threshold", threshold))
        zone = last.get("zone", zone)
        action = last.get("action_name", action)
    return RunConfig(
        threshold=threshold,
        delaySeconds=DELAY_SECONDS,
        zone=zone,
        actionName=action,
    )


# ── Routes ────────────────────────────────────────────────────────────────────


@app.get("/api/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/api/dashboard", response_model=DashboardPayload)
def get_dashboard(
    mode: Literal["sim", "sandbox", "live"] = Query(default="sandbox"),
) -> DashboardPayload:
    log_path = _resolve_log_path(mode)
    records = _read_log_records(log_path)
    cycles = _to_cycles(records)
    config = _config_from_records(records)

    return DashboardPayload(
        config=config,
        cycles=cycles,
        generatedAt=datetime.now(timezone.utc).isoformat(),
    )