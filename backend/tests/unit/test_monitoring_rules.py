"""Unit tests for Monitoring and Rule Evaluator logic."""

import unittest
from app.monitoring.rules import evaluate_measurement_rules


class TestMonitoringRulesUnit(unittest.TestCase):
    def setUp(self):
        self.profile = {
            "crop_name": "Wheat",
            "recommended_temperature_min_c": 15.0,
            "recommended_temperature_max_c": 22.0,
            "recommended_relative_humidity_min_percent": 50.0,
            "recommended_relative_humidity_max_percent": 65.0,
            "recommended_crop_moisture_percent": 11.5,
        }

    def test_within_safe_range(self):
        violations = evaluate_measurement_rules(
            temp_c=18.0,
            humidity_pct=58.0,
            moisture_pct=11.0,
            crop_profile=self.profile,
        )
        self.assertEqual(len(violations), 0)

    def test_temperature_high_warning_and_critical(self):
        # Warning: temp slightly above max (23.5°C > 22°C)
        v_warn = evaluate_measurement_rules(23.5, 55.0, None, self.profile)
        self.assertEqual(len(v_warn), 1)
        self.assertEqual(v_warn[0].condition_type, "temperature_high")
        self.assertEqual(v_warn[0].severity, "warning")

        # Critical: temp >= max + 4°C (27.0°C)
        v_crit = evaluate_measurement_rules(27.0, 55.0, None, self.profile)
        self.assertEqual(len(v_crit), 1)
        self.assertEqual(v_crit[0].severity, "critical")

    def test_humidity_high_violation(self):
        # High RH (75% > max 65%)
        violations = evaluate_measurement_rules(18.0, 75.0, None, self.profile)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].condition_type, "humidity_high")

    def test_crop_moisture_high_violation(self):
        # Safe moisture is 11.5%, reading is 13.5%
        violations = evaluate_measurement_rules(18.0, 55.0, 13.5, self.profile)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].condition_type, "moisture_high")
        self.assertEqual(violations[0].severity, "critical")


if __name__ == "__main__":
    unittest.main()
