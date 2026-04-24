"""
scheduler/carbon_scheduler.py
────────────────────────────────────────────────────────────────────────────────
Carbon-Aware Scheduler — the decision engine of the system.

Design Principles
-----------------
1. Single Responsibility  – the scheduler ONLY decides; it does NOT execute.
2. Pluggable              – BaseScheduler is an abstract interface so a future
                            ML-based or forecast-based scheduler is a drop-in.
3. No hardcoded values    – threshold comes from config / constructor argument.
4. Full traceability      – every call produces a ScheduleDecision that carries
                            all context needed for logging and analysis.

Decision Logic
--------------
    carbon_intensity > threshold  →  DELAY
    carbon_intensity ≤ threshold  →  EXECUTE
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CARBON_THRESHOLD, DELAY_SECONDS

logger = logging.getLogger(__name__)

# ── Decision model ────────────────────────────────────────────────────────────

class Decision(str, Enum):
    EXECUTE = "execute"
    DELAY   = "delay"


@dataclass
class ScheduleDecision:
    """
    Immutable record produced by the scheduler for every invocation.
    Passed downstream to the executor and persisted in the log.
    """
    decision:         Decision
    carbon_intensity: float          # gCO2/kWh at decision time
    threshold:        float          # configured threshold
    zone:             str
    decided_at:       datetime       = field(default_factory=lambda: datetime.now(timezone.utc))
    reason:           str            = ""
    delay_seconds:    Optional[int]  = None   # set when decision == DELAY

    # ── Convenience ──────────────────────────────────────────────────────────

    @property
    def should_execute(self) -> bool:
        return self.decision == Decision.EXECUTE

    @property
    def margin(self) -> float:
        """Signed distance from threshold (+ve = headroom, -ve = overshoot)."""
        return self.threshold - self.carbon_intensity

    def __str__(self) -> str:
        icon = "✅ EXECUTE" if self.should_execute else "⏸️  DELAY"
        return (
            f"{icon}  |  carbon={self.carbon_intensity:.1f}  "
            f"threshold={self.threshold:.1f}  "
            f"margin={self.margin:+.1f}  zone={self.zone}"
        )


# ── Abstract base (extensibility hook) ───────────────────────────────────────

class BaseScheduler(ABC):
    """
    Interface every scheduler must implement.

    Replacing the rule-based scheduler with an ML model in Level 2
    requires only a new subclass of BaseScheduler.
    """

    @abstractmethod
    def evaluate(self, carbon_intensity: float, zone: str) -> ScheduleDecision:
        """Return a ScheduleDecision given the current carbon intensity."""
        ...

    @property
    @abstractmethod
    def threshold(self) -> float:
        """Current effective threshold (gCO2/kWh)."""
        ...


# ── Concrete implementation — Rule-Based Scheduler ────────────────────────────

class RuleBasedScheduler(BaseScheduler):
    """
    Simple threshold scheduler (Level 1 implementation).

    Parameters
    ----------
    threshold_gco2 : float
        If carbon_intensity > threshold → DELAY, else → EXECUTE.
    delay_seconds : int
        How long to delay execution (passed through to the decision).
    """

    def __init__(
        self,
        threshold_gco2: float = CARBON_THRESHOLD,
        delay_seconds: int    = DELAY_SECONDS,
    ) -> None:
        self._threshold    = float(threshold_gco2)
        self._delay_seconds = int(delay_seconds)
        logger.info(
            "[Scheduler] RuleBasedScheduler initialised  "
            "threshold=%.1f gCO2/kWh  delay=%ds",
            self._threshold, self._delay_seconds,
        )

    # ── BaseScheduler interface ───────────────────────────────────────────────

    @property
    def threshold(self) -> float:
        return self._threshold

    def evaluate(self, carbon_intensity: float, zone: str) -> ScheduleDecision:
        """
        Core decision function.

        Args:
            carbon_intensity : live reading in gCO2/kWh
            zone             : zone identifier (for audit trail)

        Returns:
            ScheduleDecision with decision, reason, and optional delay.
        """
        carbon_intensity = float(carbon_intensity)
        over_threshold   = carbon_intensity > self._threshold

        if over_threshold:
            decision      = Decision.DELAY
            delay_seconds = self._delay_seconds
            reason = (
                f"Carbon intensity {carbon_intensity:.1f} gCO2/kWh exceeds "
                f"threshold {self._threshold:.1f} gCO2/kWh by "
                f"{carbon_intensity - self._threshold:.1f} gCO2/kWh. "
                "Execution delayed to reduce carbon footprint."
            )
        else:
            decision      = Decision.EXECUTE
            delay_seconds = None
            reason = (
                f"Carbon intensity {carbon_intensity:.1f} gCO2/kWh is within "
                f"threshold {self._threshold:.1f} gCO2/kWh "
                f"(headroom: {self._threshold - carbon_intensity:.1f} gCO2/kWh). "
                "Proceeding with immediate execution."
            )

        sd = ScheduleDecision(
            decision=decision,
            carbon_intensity=carbon_intensity,
            threshold=self._threshold,
            zone=zone,
            reason=reason,
            delay_seconds=delay_seconds,
        )

        # ── Mandatory structured log line ─────────────────────────────────────
        logger.info(
            "[Scheduler] carbon=%.1f  threshold=%.1f  decision=%-7s  zone=%s",
            carbon_intensity, self._threshold, decision.value.upper(), zone,
        )
        logger.debug("[Scheduler] Reason: %s", reason)

        return sd

    # ── Optional: dynamic threshold update (Level 2 hook) ────────────────────

    def update_threshold(self, new_threshold: float) -> None:
        """Allow runtime reconfiguration (e.g. via API endpoint in Level 2)."""
        logger.info(
            "[Scheduler] Threshold updated: %.1f → %.1f gCO2/kWh",
            self._threshold, new_threshold,
        )
        self._threshold = float(new_threshold)
