"""
main.py
────────────────────────────────────────────────────────────────────────────────
Carbon-Aware Scheduling System — Main Entry Point

Full execution flow (STRICT — no bypassing):
    ElectricityMaps API  →  Carbon Reading
         ↓
    RuleBasedScheduler   →  ScheduleDecision  (EXECUTE | DELAY)
         ↓
    Executor             →  OpenWhisk Action invocation + file logging

Usage
-----
    # Live mode (real API):
    python main.py

    # Simulation mode (reproducible demo — no API key needed):
    SIMULATION_MODE=true python main.py

    # Override threshold at runtime:
    CARBON_THRESHOLD=150 python main.py

    # Run only N cycles:
    python main.py --cycles 5

    # Specific zone:
    python main.py --zone US-CAL-CISO
"""
from __future__ import annotations
import sys
sys.stdout.reconfigure(encoding='utf-8')
import argparse
import logging
import os
import time
from datetime import datetime, timezone

# ── Pre-parse --mode so config.py picks the right log files ──────────────────
_VALID_MODES = ("sim", "sandbox", "live")
_mode = "sandbox"
if "--mode" in sys.argv:
    idx = sys.argv.index("--mode")
    if idx + 1 < len(sys.argv) and sys.argv[idx + 1] in _VALID_MODES:
        _mode = sys.argv[idx + 1]
os.environ["LOG_MODE"] = _mode

# ── Project imports ────────────────────────────────────────────────────────────
from config import (
    CARBON_THRESHOLD,
    DEFAULT_ZONE,
    DELAY_SECONDS,
    SIMULATION_MODE,
    SIMULATION_DATA,
    LOG_FILE_CSV,
    LOG_FILE_JSON,
)

from api.electricity_maps import ElectricityMapsClient, CarbonReading
from scheduler.carbon_scheduler import RuleBasedScheduler, ScheduleDecision
from executor.executor import Executor

# ── Logging configuration ─────────────────────────────────────────────────────

def setup_logging(level: str = "INFO") -> None:
    fmt = "%(asctime)s  %(levelname)-8s  %(name)-30s  %(message)s"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/system.log", mode="a"),
        ],
    )

logger = logging.getLogger(__name__)


from pathlib import Path

def get_dynamic_threshold(redis_conn, default_val: float) -> float:
    # 1. Try Redis first
    if redis_conn:
        try:
            val = redis_conn.get("carbon_threshold")
            if val is not None:
                return float(val)
        except Exception:
            pass

    # 2. Try shared JSON file
    config_file = Path("logs/dynamic_config.json")
    if config_file.exists():
        try:
            with config_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return float(data["threshold"])
        except Exception:
            pass

    return default_val



# ── Simulation data source ────────────────────────────────────────────────────

class SimulatedCarbonSource:
    """
    Replay SIMULATION_DATA for reproducible Phase-2 scenario testing.
    Returns CarbonReading objects without any network calls.
    """

    def __init__(self, zone: str = DEFAULT_ZONE) -> None:
        self._zone = zone
        self._idx  = 0

    def next(self) -> CarbonReading:
        if self._idx >= len(SIMULATION_DATA):
            self._idx = 0   # wrap around

        _, intensity = SIMULATION_DATA[self._idx]
        self._idx += 1

        return CarbonReading(
            zone=self._zone,
            carbon_intensity=float(intensity),
            fetched_at=datetime.now(timezone.utc),
            is_estimated=False,
            source="Simulation",
        )

    @property
    def remaining(self) -> int:
        return len(SIMULATION_DATA) - self._idx


# ── Main orchestration loop ───────────────────────────────────────────────────

def run(
    cycles:     int   = len(SIMULATION_DATA),
    zone:       str   = DEFAULT_ZONE,
    threshold:  float = CARBON_THRESHOLD,
    sim_mode:   bool  = SIMULATION_MODE,
    interval_s: float = 1.0,
) -> None:
    """
    Execute `cycles` scheduling decisions.

    Args:
        cycles     : number of API-fetch → schedule → execute cycles to run
        zone       : ElectricityMaps zone code
        threshold  : carbon intensity threshold (gCO2/kWh)
        sim_mode   : if True, use simulated data instead of live API
        interval_s : seconds to pause between cycles
    """
    os.makedirs("logs", exist_ok=True)
    setup_logging()

    # Reset log files for the current mode so each run starts fresh
    if os.path.exists(LOG_FILE_CSV):
        try:
            os.remove(LOG_FILE_CSV)
        except Exception:
            pass
    if os.path.exists(LOG_FILE_JSON):
        try:
            os.remove(LOG_FILE_JSON)
        except Exception:
            pass
    if os.path.exists("logs/worker.log"):
        try:
            with open("logs/worker.log", "w", encoding="utf-8") as f:
                pass
        except Exception:
            pass

    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║      Carbon-Aware Scheduling System  — STARTING         ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")
    logger.info("  Mode      : %s", "SIMULATION" if sim_mode else "LIVE API")
    logger.info("  Zone      : %s", zone)
    logger.info("  Threshold : %.1f gCO2/kWh", threshold)
    logger.info("  Cycles    : %d", cycles)
    logger.info("  Delay     : %ds when carbon > threshold", DELAY_SECONDS)

    # ── Instantiate components ────────────────────────────────────────────────
    scheduler = RuleBasedScheduler(
        threshold_gco2=threshold,
        delay_seconds=DELAY_SECONDS,
    )
    executor  = Executor(
        action_name="data_processor",
        action_params={"task_name": "carbon-aware-batch", "payload_size": 256},
        execute_after_delay=True,  # set True to actually run after delay
    )
    executor.clear_queue()

    if sim_mode:
        source = SimulatedCarbonSource(zone=zone)
        logger.info("  [Simulation] Using %d pre-defined data points.", len(SIMULATION_DATA))
    else:
        api_client = ElectricityMapsClient()
        logger.info("  [Live] Using ElectricityMaps API for zone '%s'.", zone)

    # ── Main loop ─────────────────────────────────────────────────────────────
    results = []
    for cycle in range(1, cycles + 1):
        logger.info("\n─── Cycle %d / %d ─────────────────────────────────", cycle, cycles)
        
        # Read dynamic threshold (from Redis or JSON)
        current_threshold = get_dynamic_threshold(executor._redis, threshold)
        scheduler.update_threshold(current_threshold)

        # Set dynamic task name for the current cycle
        executor._action_params = {
            "task_name": f"Request #{cycle}",
            "payload_size": 256
        }

        # 1. FETCH carbon data
        try:
            if sim_mode:
                reading: CarbonReading = source.next()
                logger.info(
                    "[Main] Simulated reading: %.1f gCO2/kWh (zone=%s)",
                    reading.carbon_intensity, reading.zone,
                )
            else:
                reading = api_client.get_carbon_intensity(zone)
            executor.update_carbon_state(reading.carbon_intensity, current_threshold)
        except RuntimeError as exc:
            logger.error("[Main] Failed to fetch carbon intensity: %s", exc)
            logger.error("[Main] Skipping cycle %d.", cycle)
            continue

        # 2. SCHEDULE — ALL decisions go through the scheduler
        decision: ScheduleDecision = scheduler.evaluate(
            carbon_intensity=reading.carbon_intensity,
            zone=reading.zone,
        )
        logger.info("[Main] Scheduler says: %s", decision)

        # 3. EXECUTE (or delay) via Executor
        result = executor.run(decision)
        logger.info(
            "[Main] Execution outcome: status=%s  duration=%s ms",
            result["execution_status"],
            result.get("execution_duration_ms", "N/A"),
        )

        results.append({
            "cycle":            cycle,
            "carbon_intensity": reading.carbon_intensity,
            "decision":         decision.decision.value,
            "status":           result["execution_status"],
        })

        if cycle < cycles:
            time.sleep(interval_s)

    # ── Summary ───────────────────────────────────────────────────────────────
    executed = sum(1 for r in results if r["decision"] == "execute")
    delayed  = sum(1 for r in results if r["decision"] == "delay")

    logger.info("\n╔══════════════════════════════════════════════════════════╗")
    logger.info("║                  SUMMARY                                ║")
    logger.info("╠══════════════════════════════════════════════════════════╣")
    logger.info("║  Total cycles  : %-39d ║", len(results))
    logger.info("║  Executed      : %-39d ║", executed)
    logger.info("║  Delayed       : %-39d ║", delayed)
    if results:
        avg_carbon = sum(r["carbon_intensity"] for r in results) / len(results)
        logger.info("║  Avg carbon    : %-36.1f gCO2 ║", avg_carbon)
    logger.info("╚══════════════════════════════════════════════════════════╝")
    logger.info("  Logs saved to: %s  &  %s", LOG_FILE_CSV, LOG_FILE_JSON)


# ── CLI interface ─────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Carbon-Aware Scheduling System for Apache OpenWhisk"
    )
    p.add_argument("--mode", type=str, default="sandbox",
               choices=["sim", "sandbox", "live"],
               help="Log dosyası modu (hangi CSV/JSON'a yazılacağı)")
    p.add_argument("--cycles",    type=int,   default=len(SIMULATION_DATA),
                   help="Number of scheduling cycles to run")
    p.add_argument("--zone",      type=str,   default=DEFAULT_ZONE,
                   help="ElectricityMaps zone code (e.g. DE, US-CAL-CISO, TR)")
    p.add_argument("--threshold", type=float, default=CARBON_THRESHOLD,
                   help="Carbon threshold in gCO2/kWh")
    p.add_argument("--sim",       action="store_true", default=SIMULATION_MODE,
                   help="Run in simulation mode (no API key required)")
    p.add_argument("--interval",  type=float, default=0.5,
                   help="Seconds between cycles")
    p.add_argument("--log-level", type=str,   default="INFO",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                   help="Logging verbosity")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(
        cycles     = args.cycles,
        zone       = args.zone,
        threshold  = args.threshold,
        sim_mode   = args.sim,
        interval_s = args.interval,
    )
