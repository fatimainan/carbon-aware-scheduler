"""
executor/executor.py
────────────────────────────────────────────────────────────────────────────────
Execution Module — bridges the scheduler decision and OpenWhisk.

Responsibilities
----------------
1. Accept a ScheduleDecision from the scheduler.
2. If EXECUTE  → invoke the OpenWhisk action and return its result.
3. If DELAY    → simulate queue-based delay, then (optionally) retry.
4. Persist every event to CSV and JSON log files (MANDATORY per spec).
5. Never call OpenWhisk directly from anywhere else in the system.

ALL function executions MUST go through this module's `run()` function.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    LOG_FILE_CSV,
    LOG_FILE_JSON,
    OPENWHISK_HOST,
    OPENWHISK_AUTH,
    OPENWHISK_NS,
)
from scheduler.carbon_scheduler import Decision, ScheduleDecision

logger = logging.getLogger(__name__)

# ── CSV column order (must stay stable for analysis) ─────────────────────────
_CSV_FIELDS = [
    "timestamp",
    "zone",
    "carbon_intensity",
    "threshold",
    "decision",
    "delay_seconds",
    "execution_status",
    "execution_duration_ms",
    "action_name",
    "task_name",
    "error",
]


# ── Main execution orchestrator ───────────────────────────────────────────────

class Executor:
    """
    Connects scheduler decisions to real OpenWhisk invocations.

    Parameters
    ----------
    action_name  : OpenWhisk action to invoke (default: "data_processor")
    action_params: default params passed to every invocation
    execute_after_delay : if True, re-invoke the action after delay period
    """

    def __init__(
        self,
        action_name: str                 = "data_processor",
        action_params: Optional[dict]    = None,
        execute_after_delay: bool        = False,
    ) -> None:
        self._action_name          = action_name
        self._action_params        = action_params or {"task_name": "carbon-aware-job", "payload_size": 512}
        self._execute_after_delay  = execute_after_delay
        self._ow_invoker           = OpenWhiskInvoker()

        # Ensure log directories exist
        Path(LOG_FILE_CSV).parent.mkdir(parents=True, exist_ok=True)
        Path(LOG_FILE_JSON).parent.mkdir(parents=True, exist_ok=True)
        self._init_csv()

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self, decision: ScheduleDecision) -> dict:
        """
        ENTRY POINT — ALL function executions flow through here.

        Args:
            decision: ScheduleDecision from the scheduler.

        Returns:
            Result dict including decision, execution outcome, and log status.
        """
        logger.info("=" * 70)
        logger.info("[Executor] Processing decision: %s", decision)

        if decision.decision == Decision.EXECUTE:
            result = self._do_execute(decision)
        else:
            result = self._do_delay(decision)

        # ── Mandatory file logging ─────────────────────────────────────────
        self._log_to_csv(decision, result)
        self._log_to_json(decision, result)

        logger.info("[Executor] ✅ Event logged to CSV and JSON.")
        logger.info("=" * 70)
        return result

    # ── Execution path ────────────────────────────────────────────────────────

    def _do_execute(self, decision: ScheduleDecision) -> dict:
        logger.info(
            "[Executor] 🟢 EXECUTING action '%s'  (carbon=%.1f ≤ threshold=%.1f)",
            self._action_name, decision.carbon_intensity, decision.threshold,
        )
        ow_result = self._ow_invoker.invoke(
            self._action_name, self._action_params
        )
        return {
            "execution_status":      "executed",
            "execution_duration_ms": ow_result.get("duration_ms"),
            "action_result":         ow_result,
            "error":                 None,
        }

    # ── Delay path ────────────────────────────────────────────────────────────

    def _do_delay(self, decision: ScheduleDecision) -> dict:
        delay = decision.delay_seconds or 0
        logger.warning(
            "[Executor] 🔴 DELAYING execution for %ds  "
            "(carbon=%.1f > threshold=%.1f)",
            delay, decision.carbon_intensity, decision.threshold,
        )

        # Simulate queue-based delay
        logger.info("[Executor] ⏳ Task queued.  Sleeping %ds …", delay)
        time.sleep(delay)
        logger.info("[Executor] ⏰ Delay period elapsed.")

        if self._execute_after_delay:
            logger.info("[Executor] Retrying execution after delay …")
            ow_result = self._ow_invoker.invoke(
                self._action_name, self._action_params
            )
            return {
                "execution_status":      "delayed_then_executed",
                "execution_duration_ms": ow_result.get("duration_ms"),
                "action_result":         ow_result,
                "error":                 None,
            }

        return {
            "execution_status":      "delayed",
            "execution_duration_ms": None,
            "action_result":         None,
            "error":                 None,
        }

    # ── Logging helpers ───────────────────────────────────────────────────────

    def _init_csv(self) -> None:
        """Create CSV with header row if it doesn't exist."""
        if not Path(LOG_FILE_CSV).exists():
            with open(LOG_FILE_CSV, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
                writer.writeheader()
            logger.info("[Executor] Created log file: %s", LOG_FILE_CSV)

    def _log_to_csv(self, decision: ScheduleDecision, result: dict) -> None:
        row = {
            "timestamp":             decision.decided_at.isoformat(),
            "zone":                  decision.zone,
            "carbon_intensity":      decision.carbon_intensity,
            "threshold":             decision.threshold,
            "decision":              decision.decision.value,
            "delay_seconds":         decision.delay_seconds or "",
            "execution_status":      result["execution_status"],
            "execution_duration_ms": result.get("execution_duration_ms") or "",
            "action_name":           self._action_name,
            "task_name":             self._action_params.get("task_name", ""),
            "error":                 result.get("error") or "",
        }
        with open(LOG_FILE_CSV, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
            writer.writerow(row)

    def _log_to_json(self, decision: ScheduleDecision, result: dict) -> None:
        """Append a JSON record to the log file (newline-delimited JSON)."""
        record = {
            "timestamp":        decision.decided_at.isoformat(),
            "zone":             decision.zone,
            "carbon_intensity": decision.carbon_intensity,
            "threshold":        decision.threshold,
            "decision":         decision.decision.value,
            "delay_seconds":    decision.delay_seconds,
            "reason":           decision.reason,
            "execution_status": result["execution_status"],
            "duration_ms":      result.get("execution_duration_ms"),
            "action_name":      self._action_name,
            "task_name":        self._action_params.get("task_name"),
            "error":            result.get("error"),
        }
        with open(LOG_FILE_JSON, "a") as f:
            f.write(json.dumps(record) + "\n")


# ── OpenWhisk HTTP invoker ────────────────────────────────────────────────────

class OpenWhiskInvoker:
    """
    Direct HTTP client for the OpenWhisk REST API.

    Endpoint: POST /api/v1/namespaces/{ns}/actions/{action}?blocking=true
    """

    def __init__(
        self,
        host: str = OPENWHISK_HOST,
        auth: str = OPENWHISK_AUTH,
        namespace: str = OPENWHISK_NS,
        timeout: int = 60,
    ) -> None:
        self._host      = host.rstrip("/")
        self._auth      = tuple(auth.split(":", 1)) if ":" in auth else (auth, "")
        self._namespace = namespace
        self._timeout   = timeout

    def invoke(self, action_name: str, params: dict) -> dict:
        """
        Invoke an OpenWhisk action and return its result.

        Falls back to local direct invocation if OpenWhisk is unreachable
        (allows full demo without a running OpenWhisk cluster).
        """
        url = (
            f"{self._host}/api/v1/namespaces/{self._namespace}"
            f"/actions/{action_name}?blocking=true&result=true"
        )
        try:
            response = requests.post(
                url,
                json=params,
                auth=self._auth,
                timeout=self._timeout,
                verify=False,   # self-signed cert in local OW deployments
            )
            response.raise_for_status()
            result = response.json()
            logger.info("[OW] Action '%s' completed: %s", action_name, result.get("status"))
            return result

        except requests.exceptions.ConnectionError:
            logger.warning(
                "[OW] OpenWhisk not reachable at %s — running action locally.",
                self._host,
            )
            return self._invoke_locally(action_name, params)

        except Exception as exc:                    # noqa: BLE001
            logger.error("[OW] Invocation error: %s", exc)
            return self._invoke_locally(action_name, params)

    @staticmethod
    def _invoke_locally(action_name: str, params: dict) -> dict:
        """
        Fallback: import and run the action function directly.
        This makes the demo fully runnable without a live OpenWhisk cluster.
        """
        logger.info("[OW] ⚙️  Local invocation of '%s'", action_name)
        try:
            import importlib
            mod = importlib.import_module(f"functions.{action_name}")
            result = mod.main(params)
            logger.info("[OW] Local result: %s", result.get("status"))
            return result
        except Exception as exc:                    # noqa: BLE001
            return {"status": "error", "error": str(exc)}
