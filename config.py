"""
config.py — Centralized configuration for the Carbon-Aware Scheduling System.
All tuneable parameters live here; no hardcoded values elsewhere.
"""

import os

# ── ElectricityMaps API ────────────────────────────────────────────────────────
ELECTRICITY_MAPS_API_KEY = os.getenv("ELECTRICITY_MAPS_API_KEY", "YOUR_API_KEY_HERE")
ELECTRICITY_MAPS_BASE_URL = "https://api.electricitymap.org/v3"

# Default zone (ISO 3166-1 alpha-2 based zone codes, e.g. "DE" for Germany,
# "US-CAL-CISO" for California, "TR" for Turkey)
DEFAULT_ZONE = os.getenv("CARBON_ZONE", "TR")

# ── Scheduler ─────────────────────────────────────────────────────────────────
# Carbon intensity threshold in gCO2/kWh.
# Executions are DELAYED when actual intensity > this value.
CARBON_THRESHOLD = float(os.getenv("CARBON_THRESHOLD", "350"))

# Delay duration (seconds) used by the queue-based delay simulation
DELAY_SECONDS = int(os.getenv("DELAY_SECONDS", "30"))

# ── OpenWhisk ─────────────────────────────────────────────────────────────────
OPENWHISK_HOST = os.getenv("OPENWHISK_HOST", "http://localhost:3233")
OPENWHISK_AUTH = os.getenv("OPENWHISK_AUTH",
                            "23bc46b1-71f6-4ed5-8c54-816aa4f8c502:"
                            "123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP")
OPENWHISK_NS    = os.getenv("OPENWHISK_NAMESPACE", "guest")

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_MODE = os.getenv("LOG_MODE", "sandbox")  # "sim" | "sandbox" | "live"
LOG_FILE_CSV  = f"logs/execution_log_{LOG_MODE}.csv"
LOG_FILE_JSON = f"logs/execution_log_{LOG_MODE}.json"

# ── Simulation (Phase 2 scenario testing) ────────────────────────────────────
# When True the system reads carbon values from SIMULATION_DATA instead of
# calling the live API; useful for reproducible demos / CI.
SIMULATION_MODE = os.getenv("SIMULATION_MODE", "false").lower() == "true"

SIMULATION_DATA = [
    # (timestamp_offset_minutes, carbon_gco2_kwh)
    (0,   85),    # Scenario A – low  → EXECUTE
    (5,   110),   # Scenario A – low  → EXECUTE
    (10,  160),   # Scenario A – mid  → EXECUTE
    (15,  210),   # Scenario B – high → DELAY
    (20,  275),   # Scenario B – high → DELAY
    (25,  320),   # Scenario B – high → DELAY
    (30,  180),   # Scenario A – low  → EXECUTE
    (35,  95),    # Scenario A – low  → EXECUTE
    (40,  240),   # Scenario B – high → DELAY
    (45,  130),   # Scenario A – low  → EXECUTE
]
