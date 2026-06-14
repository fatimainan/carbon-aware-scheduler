"""
executor/executor.py
────────────────────────────────────────────────────────────────────────────────
Execution Module — bridges the scheduler decision and OpenWhisk.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import redis
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


class Executor:

    def __init__(
        self,
        action_name: str              = "data_processor",
        action_params: Optional[dict] = None,
        execute_after_delay: bool     = True,
    ) -> None:
        self._action_name   = action_name
        self.execute_after_delay = execute_after_delay
        self._action_params = action_params or {"task_name": "carbon-aware-job", "payload_size": 512}
        self._ow_invoker    = OpenWhiskInvoker()

        # Redis bağlantısı
        is_docker = os.path.exists("/.dockerenv")
        default_redis_host = "redis" if is_docker else "localhost"
        redis_host = os.getenv("REDIS_HOST", default_redis_host)
        try:
            self._redis = redis.Redis(
                host=redis_host,
                port=6379,
                decode_responses=True,
                socket_connect_timeout=1.5,
                socket_timeout=1.5,
            )
            self._redis.ping()
            logger.info("[Executor] Redis connected at %s:6379", redis_host)
        except Exception:
            if redis_host != "localhost":
                try:
                    self._redis = redis.Redis(
                        host="localhost",
                        port=6379,
                        decode_responses=True,
                        socket_connect_timeout=1.5,
                        socket_timeout=1.5,
                    )
                    self._redis.ping()
                    logger.info("[Executor] Redis connected at localhost:6379 (fallback)")
                except Exception:
                    self._redis = None
                    logger.warning("[Executor] Redis not available — delay will use sleep fallback")
            else:
                self._redis = None
                logger.warning("[Executor] Redis not available — delay will use sleep fallback")

        Path(LOG_FILE_CSV).parent.mkdir(parents=True, exist_ok=True)
        Path(LOG_FILE_JSON).parent.mkdir(parents=True, exist_ok=True)
        self._init_csv()

    # ── Public API ────────────────────────────────────────────────────────────

    def clear_queue(self) -> None:
        if self._redis:
            try:
                self._redis.delete("carbon_task_queue")
                self._redis.set("clear_worker_logs", "true")
                logger.info("[Executor] Cleared existing tasks and requested worker log reset.")
            except Exception as e:
                logger.warning("[Executor] Failed to clear Redis queue: %s", e)

    def run(self, decision: ScheduleDecision) -> dict:
        logger.info("=" * 70)
        logger.info("[Executor] Processing decision: %s", decision)

        if decision.decision == Decision.EXECUTE:
            result = self._do_execute(decision)
        else:
            result = self._do_delay(decision)

        self._log_to_csv(decision, result)
        self._log_to_json(decision, result)

        logger.info("[Executor] ✅ Event logged to CSV and JSON.")
        logger.info("=" * 70)
        return result

    # ── Execute path ──────────────────────────────────────────────────────────

    def _do_execute(self, decision: ScheduleDecision) -> dict:
        logger.info(
            "[Executor] 🟢 EXECUTING action '%s'  (carbon=%.1f ≤ threshold=%.1f)",
            self._action_name, decision.carbon_intensity, decision.threshold,
        )
        ow_result = self._ow_invoker.invoke(self._action_name, self._action_params)
        return {
            "execution_status":      "executed",
            "execution_duration_ms": ow_result.get("duration_ms"),
            "action_result":         ow_result,
            "error":                 None,
        }

    # ── Delay path — Redis queue ──────────────────────────────────────────────

    def _do_delay(self, decision: ScheduleDecision) -> dict:
        logger.warning(
            "[Executor] 🔴 DELAYING  (carbon=%.1f > threshold=%.1f)",
            decision.carbon_intensity, decision.threshold,
        )

        if self._redis:
            # ── Redis queue path ──────────────────────────────────────────────
            task = {
                "action_name":    self._action_name,
                "params":         self._action_params,
                "retry_after":    time.time() + (decision.delay_seconds or 30),
                "carbon_at_delay": decision.carbon_intensity,
                "threshold":      decision.threshold,
                "zone":           decision.zone,
            }
            self._redis.rpush("carbon_task_queue", json.dumps(task))
            logger.info("[Executor] ⏳ Task pushed to Redis queue.")
            return {
                "execution_status":      "queued",
                "execution_duration_ms": None,
                "action_result":         None,
                "error":                 None,
            }
        else:
            # ── Fallback: sleep (Redis yoksa) ─────────────────────────────────
            delay = decision.delay_seconds or 30
            logger.info("[Executor] ⏳ Redis unavailable. Sleeping %ds …", delay)
            time.sleep(delay)
            return {
                "execution_status":      "delayed",
                "execution_duration_ms": None,
                "action_result":         None,
                "error":                 None,
            }

    def update_carbon_state(self, intensity: float, threshold: float):
        if self._redis:
            state = {"intensity": intensity, "threshold": threshold, "updated_at": time.time()}
            self._redis.set("current_carbon_state", json.dumps(state))
            logger.info("[Executor] 📡 Carbon state updated in Redis: %.1f gCO2", intensity)

    # ── Logging ───────────────────────────────────────────────────────────────

    def _init_csv(self) -> None:
        if not Path(LOG_FILE_CSV).exists():
            with open(LOG_FILE_CSV, "w", newline="") as f:
                csv.DictWriter(f, fieldnames=_CSV_FIELDS).writeheader()
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
            csv.DictWriter(f, fieldnames=_CSV_FIELDS).writerow(row)

    def _log_to_json(self, decision: ScheduleDecision, result: dict) -> None:
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


# ── OpenWhisk invoker ─────────────────────────────────────────────────────────

class OpenWhiskInvoker:

    def __init__(
        self,
        host: str      = OPENWHISK_HOST,
        auth: str      = OPENWHISK_AUTH,
        namespace: str = OPENWHISK_NS,
        timeout: int   = 60,
    ) -> None:
        self._host      = host.rstrip("/")
        self._auth      = tuple(auth.split(":", 1)) if ":" in auth else (auth, "")
        self._namespace = namespace
        self._timeout   = timeout

    def invoke(self, action_name: str, params: dict) -> dict:
        url = (
            f"{self._host}/api/v1/namespaces/{self._namespace}"
            f"/actions/{action_name}?blocking=true&result=true"
        )
        try:
            response = requests.post(
                url, json=params, auth=self._auth,
                timeout=self._timeout, verify=False,
            )
            response.raise_for_status()
            result = response.json()
            logger.info("[OW] Action '%s' completed: %s", action_name, result.get("status"))
            return result
        except requests.exceptions.ConnectionError:
            logger.warning("[OW] OpenWhisk not reachable — running action locally.")
            return self._invoke_locally(action_name, params)
        except Exception as exc:
            logger.error("[OW] Invocation error: %s", exc)
            return self._invoke_locally(action_name, params)

    @staticmethod
    def _invoke_locally(action_name: str, params: dict) -> dict:
        logger.info("[OW] ⚙️  Local invocation of '%s'", action_name)
        try:
            import importlib
            mod = importlib.import_module(f"functions.{action_name}")
            result = mod.main(params)
            logger.info("[OW] Local result: %s", result.get("status"))
            return result
        except Exception as exc:
            return {"status": "error", "error": str(exc)}