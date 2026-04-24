"""
api/electricity_maps.py
────────────────────────────────────────────────────────────────────────────────
ElectricityMaps API integration module.

Responsibilities
----------------
* Fetch real-time carbon intensity (gCO2eq/kWh) for a given zone.
* Expose a clean, type-safe interface so the rest of the system never
  touches raw HTTP logic.
* Abstract the provider so a future replacement (e.g. WattTime) only
  requires changing this file.

API Docs: https://static.electricitymaps.com/api/docs/index.html
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import requests

# Project-level imports
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    ELECTRICITY_MAPS_API_KEY,
    ELECTRICITY_MAPS_BASE_URL,
    DEFAULT_ZONE,
)

logger = logging.getLogger(__name__)

# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class CarbonReading:
    """Immutable snapshot of a single carbon-intensity measurement."""
    zone: str
    carbon_intensity: float          # gCO2eq/kWh
    fetched_at: datetime
    is_estimated: bool = False
    source: str = "ElectricityMaps"

    def __str__(self) -> str:
        est = " [estimated]" if self.is_estimated else ""
        return (
            f"CarbonReading(zone={self.zone}, "
            f"intensity={self.carbon_intensity:.1f} gCO2/kWh{est}, "
            f"at={self.fetched_at.isoformat()})"
        )


# ── Public interface ──────────────────────────────────────────────────────────

class ElectricityMapsClient:
    """
    Thin wrapper around the ElectricityMaps REST API.

    Usage
    -----
    client = ElectricityMapsClient()
    reading = client.get_carbon_intensity()          # uses DEFAULT_ZONE
    reading = client.get_carbon_intensity("US-CAL-CISO")
    """

    _ENDPOINT = "/carbon-intensity/latest"

    def __init__(
        self,
        api_key: str = ELECTRICITY_MAPS_API_KEY,
        base_url: str = ELECTRICITY_MAPS_BASE_URL,
        timeout: int = 10,
        max_retries: int = 3,
    ) -> None:
        self._api_key    = api_key
        self._base_url   = base_url.rstrip("/")
        self._timeout    = timeout
        self._max_retries = max_retries
        self._session    = requests.Session()
        self._session.headers.update({
            "auth-token": self._api_key,
            "Accept": "application/json",
        })

    # ── Public methods ────────────────────────────────────────────────────────

    def get_carbon_intensity(self, zone: str = DEFAULT_ZONE) -> CarbonReading:
        """
        Fetch the latest carbon intensity for *zone*.

        Returns
        -------
        CarbonReading  with real API data.

        Raises
        ------
        RuntimeError  if all retries fail.
        """
        url = f"{self._base_url}{self._ENDPOINT}"
        params = {"zone": zone}

        last_exc: Optional[Exception] = None
        for attempt in range(1, self._max_retries + 1):
            try:
                logger.debug(
                    "[API] GET %s  zone=%s  attempt=%d/%d",
                    url, zone, attempt, self._max_retries,
                )
                response = self._session.get(
                    url, params=params, timeout=self._timeout
                )
                response.raise_for_status()
                return self._parse(response.json(), zone)

            except requests.exceptions.HTTPError as exc:
                status = exc.response.status_code if exc.response else "?"
                logger.warning(
                    "[API] HTTP %s for zone=%s (attempt %d/%d)",
                    status, zone, attempt, self._max_retries,
                )
                # 401/403 → fail fast, no point retrying
                if status in (401, 403):
                    raise RuntimeError(
                        f"ElectricityMaps auth error ({status}). "
                        "Check your ELECTRICITY_MAPS_API_KEY."
                    ) from exc
                last_exc = exc

            except requests.exceptions.RequestException as exc:
                logger.warning(
                    "[API] Network error on attempt %d/%d: %s",
                    attempt, self._max_retries, exc,
                )
                last_exc = exc

            if attempt < self._max_retries:
                backoff = 2 ** attempt
                logger.info("[API] Retrying in %ds …", backoff)
                time.sleep(backoff)

        raise RuntimeError(
            f"Failed to fetch carbon intensity after {self._max_retries} "
            f"attempts. Last error: {last_exc}"
        )

    def health_check(self) -> bool:
        """Return True if the API is reachable with the configured key."""
        try:
            self.get_carbon_intensity()
            return True
        except Exception:
            return False

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _parse(payload: dict, zone: str) -> CarbonReading:
        """Convert raw JSON response to a CarbonReading."""
        try:
            intensity    = float(payload["carbonIntensity"])
            is_estimated = payload.get("isEstimated", False)
            fetched_at   = datetime.now(timezone.utc)

            logger.info(
                "[API] ✅ zone=%-20s  intensity=%.1f gCO2/kWh  estimated=%s",
                zone, intensity, is_estimated,
            )
            return CarbonReading(
                zone=zone,
                carbon_intensity=intensity,
                fetched_at=fetched_at,
                is_estimated=is_estimated,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(
                f"Unexpected API response format: {payload}"
            ) from exc


# ── Convenience function (used by main.py and tests) ─────────────────────────

def fetch_carbon_intensity(zone: str = DEFAULT_ZONE) -> CarbonReading:
    """Module-level shortcut that creates a default client and fetches data."""
    client = ElectricityMapsClient()
    return client.get_carbon_intensity(zone)
