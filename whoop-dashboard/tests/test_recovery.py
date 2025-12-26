"""Tests for WHOOP-style recovery calculation."""

import pytest
from unittest.mock import MagicMock

# Import the calculate_recovery function from CLI
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from whoop_dashboard.cli import calculate_recovery, get_recovery_color


class TestRecoveryCalculation:
    """Test recovery score calculation."""

    def test_recovery_with_all_factors(self):
        """Recovery with body battery, HRV, and sleep data."""
        wellness = MagicMock()
        wellness.stress = MagicMock()
        wellness.stress.body_battery_charged = 80
        wellness.hrv = MagicMock()
        wellness.hrv.hrv_last_night_avg = 50
        wellness.hrv.hrv_weekly_avg = 45
        wellness.sleep = MagicMock()
        wellness.sleep.total_sleep_hours = 7.5
        wellness.sleep.deep_sleep_pct = 18

        recovery = calculate_recovery(wellness)

        # Should be average of 3 factors (body_battery=80, hrv~108, sleep~93)
        assert 80 <= recovery <= 95
        assert isinstance(recovery, int)

    def test_recovery_high_hrv_above_baseline(self):
        """Higher HRV than baseline should boost recovery."""
        wellness = MagicMock()
        wellness.stress = MagicMock()
        wellness.stress.body_battery_charged = 70
        wellness.hrv = MagicMock()
        wellness.hrv.hrv_last_night_avg = 60  # 20% above baseline
        wellness.hrv.hrv_weekly_avg = 50
        wellness.sleep = MagicMock()
        wellness.sleep.total_sleep_hours = 8
        wellness.sleep.deep_sleep_pct = 20

        recovery = calculate_recovery(wellness)
        assert recovery >= 70

    def test_recovery_low_hrv_below_baseline(self):
        """Lower HRV than baseline should lower recovery."""
        wellness = MagicMock()
        wellness.stress = MagicMock()
        wellness.stress.body_battery_charged = 50
        wellness.hrv = MagicMock()
        wellness.hrv.hrv_last_night_avg = 35  # 30% below baseline
        wellness.hrv.hrv_weekly_avg = 50
        wellness.sleep = MagicMock()
        wellness.sleep.total_sleep_hours = 5
        wellness.sleep.deep_sleep_pct = 10

        recovery = calculate_recovery(wellness)
        # Low but not terrible (50 + 77.5 + 62 = 189 / 3 = 63)
        assert recovery < 70

    def test_recovery_no_data(self):
        """No data should return 0."""
        wellness = MagicMock()
        wellness.stress = None
        wellness.hrv = None
        wellness.sleep = None

        recovery = calculate_recovery(wellness)
        assert recovery == 0

    def test_recovery_only_sleep(self):
        """Recovery with only sleep data."""
        wellness = MagicMock()
        wellness.stress = None
        wellness.hrv = None
        wellness.sleep = MagicMock()
        wellness.sleep.total_sleep_hours = 8
        wellness.sleep.deep_sleep_pct = 20

        recovery = calculate_recovery(wellness)
        assert 80 <= recovery <= 100

    def test_recovery_only_body_battery(self):
        """Recovery with only body battery."""
        wellness = MagicMock()
        wellness.stress = MagicMock()
        wellness.stress.body_battery_charged = 75
        wellness.hrv = None
        wellness.sleep = None

        recovery = calculate_recovery(wellness)
        assert recovery == 75

    def test_recovery_partial_hrv_data(self):
        """HRV with missing weekly average shouldn't contribute."""
        wellness = MagicMock()
        wellness.stress = MagicMock()
        wellness.stress.body_battery_charged = 60
        wellness.hrv = MagicMock()
        wellness.hrv.hrv_last_night_avg = 45
        wellness.hrv.hrv_weekly_avg = None
        wellness.sleep = None

        recovery = calculate_recovery(wellness)
        # Only body battery contributes
        assert recovery == 60


class TestRecoveryColor:
    """Test recovery color coding."""

    def test_green_recovery(self):
        """High recovery (67+) should be green."""
        color = get_recovery_color(75)
        assert "\033[92m" in color  # Green ANSI

    def test_yellow_recovery(self):
        """Medium recovery (34-66) should be yellow."""
        color = get_recovery_color(50)
        assert "\033[93m" in color  # Yellow ANSI

    def test_red_recovery(self):
        """Low recovery (<34) should be red."""
        color = get_recovery_color(25)
        assert "\033[91m" in color  # Red ANSI

    def test_boundary_green_yellow(self):
        """67 should be green, 66 should be yellow."""
        assert "\033[92m" in get_recovery_color(67)
        assert "\033[93m" in get_recovery_color(66)

    def test_boundary_yellow_red(self):
        """34 should be yellow, 33 should be red."""
        assert "\033[93m" in get_recovery_color(34)
        assert "\033[91m" in get_recovery_color(33)


class TestRecoveryEdgeCases:
    """Edge cases for recovery calculation."""

    def test_perfect_recovery(self):
        """Maximum values should approach 100."""
        wellness = MagicMock()
        wellness.stress = MagicMock()
        wellness.stress.body_battery_charged = 100
        wellness.hrv = MagicMock()
        wellness.hrv.hrv_last_night_avg = 80
        wellness.hrv.hrv_weekly_avg = 50  # 60% above baseline
        wellness.sleep = MagicMock()
        wellness.sleep.total_sleep_hours = 9
        wellness.sleep.deep_sleep_pct = 25

        recovery = calculate_recovery(wellness)
        assert recovery >= 90

    def test_zero_sleep_hours(self):
        """Zero sleep hours should still work."""
        wellness = MagicMock()
        wellness.stress = MagicMock()
        wellness.stress.body_battery_charged = 30
        wellness.hrv = None
        wellness.sleep = MagicMock()
        wellness.sleep.total_sleep_hours = 0
        wellness.sleep.deep_sleep_pct = 0

        recovery = calculate_recovery(wellness)
        # Should still calculate something
        assert isinstance(recovery, int)

    def test_extremely_high_hrv_capped(self):
        """HRV contribution should be capped at 100."""
        wellness = MagicMock()
        wellness.stress = None
        wellness.hrv = MagicMock()
        wellness.hrv.hrv_last_night_avg = 150  # Very high
        wellness.hrv.hrv_weekly_avg = 50
        wellness.sleep = None

        recovery = calculate_recovery(wellness)
        assert recovery == 100  # Capped
