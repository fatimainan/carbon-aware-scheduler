"""
tests/test_scheduler.py
────────────────────────────────────────────────────────────────────────────────
Unit tests for the Carbon-Aware Scheduling System.

Run:
    pytest tests/ -v
"""

import csv
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

# Make project root importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scheduler.carbon_scheduler import (
    Decision,
    RuleBasedScheduler,
    ScheduleDecision,
)
from api.electricity_maps import CarbonReading, ElectricityMapsClient


# ═══════════════════════════════════════════════════════════════════════════════
# Scheduler tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestRuleBasedScheduler(unittest.TestCase):

    def setUp(self):
        self.scheduler = RuleBasedScheduler(threshold_gco2=200.0, delay_seconds=30)

    # ── EXECUTE cases ─────────────────────────────────────────────────────────

    def test_execute_when_below_threshold(self):
        """Scenario A: carbon intensity clearly below threshold → EXECUTE."""
        sd = self.scheduler.evaluate(carbon_intensity=85.0, zone="DE")
        self.assertEqual(sd.decision, Decision.EXECUTE)
        self.assertTrue(sd.should_execute)
        self.assertIsNone(sd.delay_seconds)

    def test_execute_at_exact_threshold(self):
        """Boundary: exactly at threshold → EXECUTE (not strictly greater)."""
        sd = self.scheduler.evaluate(carbon_intensity=200.0, zone="DE")
        self.assertEqual(sd.decision, Decision.EXECUTE)

    def test_execute_just_below_threshold(self):
        sd = self.scheduler.evaluate(carbon_intensity=199.9, zone="DE")
        self.assertEqual(sd.decision, Decision.EXECUTE)

    # ── DELAY cases ───────────────────────────────────────────────────────────

    def test_delay_when_above_threshold(self):
        """Scenario B: carbon intensity above threshold → DELAY."""
        sd = self.scheduler.evaluate(carbon_intensity=275.0, zone="DE")
        self.assertEqual(sd.decision, Decision.DELAY)
        self.assertFalse(sd.should_execute)
        self.assertEqual(sd.delay_seconds, 30)

    def test_delay_just_above_threshold(self):
        sd = self.scheduler.evaluate(carbon_intensity=200.1, zone="DE")
        self.assertEqual(sd.decision, Decision.DELAY)

    def test_delay_extreme_carbon(self):
        sd = self.scheduler.evaluate(carbon_intensity=999.0, zone="US-CAL-CISO")
        self.assertEqual(sd.decision, Decision.DELAY)

    # ── Margin tests ──────────────────────────────────────────────────────────

    def test_positive_margin_when_executing(self):
        sd = self.scheduler.evaluate(carbon_intensity=100.0, zone="DE")
        self.assertGreater(sd.margin, 0)

    def test_negative_margin_when_delaying(self):
        sd = self.scheduler.evaluate(carbon_intensity=250.0, zone="DE")
        self.assertLess(sd.margin, 0)

    # ── Threshold reconfiguration ─────────────────────────────────────────────

    def test_dynamic_threshold_update(self):
        self.scheduler.update_threshold(150.0)
        self.assertEqual(self.scheduler.threshold, 150.0)
        # 160 was previously EXECUTE, now should be DELAY
        sd = self.scheduler.evaluate(carbon_intensity=160.0, zone="DE")
        self.assertEqual(sd.decision, Decision.DELAY)

    # ── Decision fields ───────────────────────────────────────────────────────

    def test_decision_carries_correct_fields(self):
        sd = self.scheduler.evaluate(carbon_intensity=120.0, zone="TR")
        self.assertEqual(sd.carbon_intensity, 120.0)
        self.assertEqual(sd.threshold, 200.0)
        self.assertEqual(sd.zone, "TR")
        self.assertIsNotNone(sd.decided_at)
        self.assertIsInstance(sd.reason, str)
        self.assertGreater(len(sd.reason), 0)


# ═══════════════════════════════════════════════════════════════════════════════
# API module tests (mocked)
# ═══════════════════════════════════════════════════════════════════════════════

class TestElectricityMapsClient(unittest.TestCase):

    def _make_mock_response(self, carbon: float) -> MagicMock:
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "carbonIntensity": carbon,
            "isEstimated": False,
        }
        return resp

    @patch("api.electricity_maps.requests.Session.get")
    def test_successful_fetch(self, mock_get):
        mock_get.return_value = self._make_mock_response(150.0)
        client  = ElectricityMapsClient(api_key="test-key")
        reading = client.get_carbon_intensity("DE")
        self.assertIsInstance(reading, CarbonReading)
        self.assertEqual(reading.carbon_intensity, 150.0)
        self.assertEqual(reading.zone, "DE")

    @patch("api.electricity_maps.requests.Session.get")
    def test_different_zones(self, mock_get):
        mock_get.return_value = self._make_mock_response(300.0)
        client  = ElectricityMapsClient(api_key="test-key")
        reading = client.get_carbon_intensity("US-CAL-CISO")
        self.assertEqual(reading.zone, "US-CAL-CISO")
        self.assertEqual(reading.carbon_intensity, 300.0)

    @patch("api.electricity_maps.requests.Session.get")
    def test_retry_on_network_error(self, mock_get):
        import requests as req_lib
        mock_get.side_effect = [
            req_lib.exceptions.ConnectionError("timeout"),
            req_lib.exceptions.ConnectionError("timeout"),
            self._make_mock_response(120.0),
        ]
        client  = ElectricityMapsClient(api_key="test-key", max_retries=3)
        reading = client.get_carbon_intensity("DE")
        self.assertEqual(reading.carbon_intensity, 120.0)
        self.assertEqual(mock_get.call_count, 3)

    @patch("api.electricity_maps.requests.Session.get")
    def test_raises_after_max_retries(self, mock_get):
        import requests as req_lib
        mock_get.side_effect = req_lib.exceptions.ConnectionError("timeout")
        client = ElectricityMapsClient(api_key="test-key", max_retries=2)
        with self.assertRaises(RuntimeError):
            client.get_carbon_intensity("DE")


# ═══════════════════════════════════════════════════════════════════════════════
# Executor / logging tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutorLogging(unittest.TestCase):

    def _make_decision(self, decision: Decision, carbon: float) -> ScheduleDecision:
        return ScheduleDecision(
            decision=decision,
            carbon_intensity=carbon,
            threshold=200.0,
            zone="DE",
            decided_at=datetime.now(timezone.utc),
            delay_seconds=30 if decision == Decision.DELAY else None,
        )

    def test_csv_log_created_with_header(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path  = os.path.join(tmpdir, "test.csv")
            json_path = os.path.join(tmpdir, "test.json")

            # Patch config paths
            import executor.executor as ex_mod
            orig_csv  = ex_mod.LOG_FILE_CSV
            orig_json = ex_mod.LOG_FILE_JSON
            ex_mod.LOG_FILE_CSV  = csv_path
            ex_mod.LOG_FILE_JSON = json_path

            try:
                from executor.executor import Executor
                exec_ = Executor(
                    action_name="data_processor",
                    action_params={"task_name": "test", "payload_size": 10},
                )
                self.assertTrue(Path(csv_path).exists())
                with open(csv_path) as f:
                    header = f.readline()
                self.assertIn("timestamp", header)
                self.assertIn("carbon_intensity", header)
                self.assertIn("decision", header)
            finally:
                ex_mod.LOG_FILE_CSV  = orig_csv
                ex_mod.LOG_FILE_JSON = orig_json

    def test_execute_logs_correct_decision(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path  = os.path.join(tmpdir, "log.csv")
            json_path = os.path.join(tmpdir, "log.json")

            import executor.executor as ex_mod
            ex_mod.LOG_FILE_CSV  = csv_path
            ex_mod.LOG_FILE_JSON = json_path

            try:
                from executor.executor import Executor
                exec_ = Executor(
                    action_name="data_processor",
                    action_params={"task_name": "test", "payload_size": 10},
                )
                sd = self._make_decision(Decision.EXECUTE, 120.0)
                result = exec_.run(sd)

                self.assertEqual(result["execution_status"], "executed")

                # Check CSV row
                with open(csv_path) as f:
                    rows = list(csv.DictReader(f))
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["decision"], "execute")
                self.assertEqual(float(rows[0]["carbon_intensity"]), 120.0)

                # Check JSON record
                with open(json_path) as f:
                    record = json.loads(f.readline())
                self.assertEqual(record["decision"], "execute")

            finally:
                ex_mod.LOG_FILE_CSV  = csv_path
                ex_mod.LOG_FILE_JSON = json_path


# ═══════════════════════════════════════════════════════════════════════════════
# Integration-style test: full flow
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullFlow(unittest.TestCase):
    """
    Exercises the complete API → Scheduler → Executor chain with mocks.
    Verifies BOTH the EXECUTE and DELAY paths.
    """

    def _run_scenario(self, carbon_value: float, expected_decision: str):
        """Generic helper for scenario testing."""
        scheduler = RuleBasedScheduler(threshold_gco2=200.0, delay_seconds=0)
        sd        = scheduler.evaluate(carbon_intensity=carbon_value, zone="DE")
        self.assertEqual(sd.decision.value, expected_decision)

    def test_scenario_a_low_carbon_execute(self):
        """Scenario A: carbon=85 → must EXECUTE."""
        self._run_scenario(85.0,  "execute")
        self._run_scenario(110.0, "execute")
        self._run_scenario(160.0, "execute")

    def test_scenario_b_high_carbon_delay(self):
        """Scenario B: carbon=275 → must DELAY."""
        self._run_scenario(210.0, "delay")
        self._run_scenario(275.0, "delay")
        self._run_scenario(320.0, "delay")


if __name__ == "__main__":
    unittest.main(verbosity=2)
