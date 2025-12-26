"""Tests for baseline calculations."""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta

from garmin_client.baselines import (
    calculate_rolling_average,
    calculate_direction,
    get_personal_baselines,
    calculate_recovery_with_baselines,
    save_baselines,
    get_saved_baselines,
    DirectionIndicator,
    PersonalBaselines,
)


class TestCalculateRollingAverage:
    """Tests for calculate_rolling_average function."""

    def test_basic_average(self):
        """Test basic rolling average calculation."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = calculate_rolling_average(values, days=5)
        assert result == 30.0

    def test_seven_day_average(self):
        """Test 7-day rolling average."""
        values = [50.0, 52.0, 48.0, 55.0, 53.0, 49.0, 51.0, 60.0, 70.0]
        result = calculate_rolling_average(values, days=7)
        # First 7 values: 50, 52, 48, 55, 53, 49, 51 = 358/7 = 51.14
        expected = round((50 + 52 + 48 + 55 + 53 + 49 + 51) / 7, 2)
        assert result == expected

    def test_handles_none_values(self):
        """Test that None values are filtered out."""
        values = [10.0, None, 20.0, None, 30.0]
        result = calculate_rolling_average(values, days=5)
        # Should average 10, 20, 30 = 20
        assert result == 20.0

    def test_insufficient_data_returns_none(self):
        """Test that fewer than 3 data points returns None."""
        values = [10.0, 20.0]
        result = calculate_rolling_average(values, days=7)
        assert result is None

    def test_all_none_returns_none(self):
        """Test that all None values returns None."""
        values = [None, None, None, None]
        result = calculate_rolling_average(values, days=4)
        assert result is None

    def test_empty_list_returns_none(self):
        """Test that empty list returns None."""
        result = calculate_rolling_average([], days=7)
        assert result is None

    def test_thirty_day_average(self):
        """Test 30-day rolling average."""
        values = list(range(1, 35))  # 1 to 34
        result = calculate_rolling_average(values, days=30)
        # First 30 values: 1-30, avg = 15.5
        expected = round(sum(range(1, 31)) / 30, 2)
        assert result == expected


class TestCalculateDirection:
    """Tests for calculate_direction function."""

    def test_up_direction(self):
        """Test detection of upward direction."""
        result = calculate_direction(current=55.0, baseline=50.0)
        assert result is not None
        assert result.direction == 'up'
        assert result.change_pct == 10.0
        assert result.baseline == 50.0
        assert result.current == 55.0

    def test_down_direction(self):
        """Test detection of downward direction."""
        result = calculate_direction(current=45.0, baseline=50.0)
        assert result is not None
        assert result.direction == 'down'
        assert result.change_pct == -10.0

    def test_stable_direction(self):
        """Test detection of stable (within threshold)."""
        result = calculate_direction(current=51.0, baseline=50.0, threshold_pct=5.0)
        assert result is not None
        assert result.direction == 'stable'
        assert result.change_pct == 2.0

    def test_custom_threshold(self):
        """Test custom threshold percentage."""
        # 8% change, but threshold is 10%
        result = calculate_direction(current=54.0, baseline=50.0, threshold_pct=10.0)
        assert result is not None
        assert result.direction == 'stable'

    def test_inverse_metric_rhr(self):
        """Test inverse metric (lower is better, like RHR)."""
        # RHR went down - this is good, so direction should be 'up' (improvement)
        result = calculate_direction(current=55.0, baseline=60.0, inverse=True)
        assert result is not None
        assert result.direction == 'up'  # Lower RHR is good

        # RHR went up - this is bad
        result = calculate_direction(current=65.0, baseline=60.0, inverse=True)
        assert result is not None
        assert result.direction == 'down'  # Higher RHR is bad

    def test_none_current_returns_none(self):
        """Test that None current returns None."""
        result = calculate_direction(current=None, baseline=50.0)
        assert result is None

    def test_none_baseline_returns_none(self):
        """Test that None baseline returns None."""
        result = calculate_direction(current=55.0, baseline=None)
        assert result is None

    def test_zero_baseline_returns_none(self):
        """Test that zero baseline returns None (avoid division by zero)."""
        result = calculate_direction(current=55.0, baseline=0)
        assert result is None


class TestCalculateRecoveryWithBaselines:
    """Tests for recovery calculation using personal baselines."""

    def test_all_metrics_available(self):
        """Test recovery calculation with all metrics available."""
        baselines = PersonalBaselines(
            date="2024-01-15",
            hrv_7d_avg=50.0,
            sleep_7d_avg=7.5,
            recovery_7d_avg=70.0,
        )
        recovery, factors = calculate_recovery_with_baselines(
            current_hrv=55.0,  # Above baseline
            current_sleep_hours=8.0,  # Above baseline
            current_body_battery=75.0,  # Above baseline
            baselines=baselines,
        )
        assert recovery > 0
        assert 'hrv' in factors
        assert 'sleep' in factors
        assert 'body_battery' in factors

    def test_hrv_weighted_higher(self):
        """Test that HRV is weighted 1.5x."""
        baselines = PersonalBaselines(
            date="2024-01-15",
            hrv_7d_avg=50.0,
            sleep_7d_avg=7.5,
        )
        _, factors = calculate_recovery_with_baselines(
            current_hrv=50.0,
            current_sleep_hours=7.5,
            current_body_battery=None,
            baselines=baselines,
        )
        assert factors['hrv']['weight'] == 1.5
        assert factors['sleep']['weight'] == 1.0

    def test_no_metrics_returns_zero(self):
        """Test that no metrics returns 0 recovery."""
        baselines = PersonalBaselines(date="2024-01-15")
        recovery, factors = calculate_recovery_with_baselines(
            current_hrv=None,
            current_sleep_hours=None,
            current_body_battery=None,
            baselines=baselines,
        )
        assert recovery == 0
        assert len(factors) == 0

    def test_body_battery_only(self):
        """Test recovery with only body battery available."""
        baselines = PersonalBaselines(
            date="2024-01-15",
            recovery_7d_avg=60.0,
        )
        recovery, factors = calculate_recovery_with_baselines(
            current_hrv=None,
            current_sleep_hours=None,
            current_body_battery=80.0,
            baselines=baselines,
        )
        assert recovery == 80  # Direct body battery value
        assert 'body_battery' in factors

    def test_direction_indicators_included(self):
        """Test that direction indicators are included in factors."""
        baselines = PersonalBaselines(
            date="2024-01-15",
            hrv_7d_avg=50.0,
            sleep_7d_avg=7.0,
        )
        _, factors = calculate_recovery_with_baselines(
            current_hrv=55.0,  # 10% above baseline
            current_sleep_hours=7.7,  # 10% above baseline
            current_body_battery=None,
            baselines=baselines,
        )
        assert factors['hrv']['direction'] is not None
        assert factors['hrv']['direction'].direction == 'up'
        assert factors['sleep']['direction'] is not None
        assert factors['sleep']['direction'].direction == 'up'


class TestDatabaseOperations:
    """Tests for database save/load operations."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        conn = sqlite3.connect(path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS daily_wellness (
                date TEXT PRIMARY KEY,
                fetched_at TEXT NOT NULL,
                resting_heart_rate INTEGER,
                training_readiness_score INTEGER,
                training_readiness_level TEXT,
                raw_json TEXT
            );

            CREATE TABLE IF NOT EXISTS hrv_data (
                date TEXT PRIMARY KEY,
                hrv_weekly_avg INTEGER,
                hrv_last_night_avg INTEGER,
                hrv_last_night_5min_high INTEGER,
                hrv_status TEXT,
                baseline_low INTEGER,
                baseline_balanced_low INTEGER,
                baseline_balanced_upper INTEGER
            );

            CREATE TABLE IF NOT EXISTS sleep_data (
                date TEXT PRIMARY KEY,
                sleep_start TEXT,
                sleep_end TEXT,
                total_sleep_seconds INTEGER DEFAULT 0,
                deep_sleep_seconds INTEGER DEFAULT 0,
                light_sleep_seconds INTEGER DEFAULT 0,
                rem_sleep_seconds INTEGER DEFAULT 0,
                awake_seconds INTEGER DEFAULT 0,
                sleep_score INTEGER,
                sleep_efficiency REAL,
                avg_spo2 REAL,
                avg_respiration REAL
            );

            CREATE TABLE IF NOT EXISTS stress_data (
                date TEXT PRIMARY KEY,
                avg_stress_level INTEGER,
                max_stress_level INTEGER,
                rest_stress_duration INTEGER DEFAULT 0,
                low_stress_duration INTEGER DEFAULT 0,
                medium_stress_duration INTEGER DEFAULT 0,
                high_stress_duration INTEGER DEFAULT 0,
                body_battery_charged INTEGER,
                body_battery_drained INTEGER,
                body_battery_high INTEGER,
                body_battery_low INTEGER
            );

            CREATE TABLE IF NOT EXISTS activity_data (
                date TEXT PRIMARY KEY,
                steps INTEGER DEFAULT 0,
                steps_goal INTEGER DEFAULT 10000,
                total_distance_m INTEGER DEFAULT 0,
                active_calories INTEGER,
                total_calories INTEGER,
                intensity_minutes INTEGER DEFAULT 0,
                floors_climbed INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS baselines (
                date TEXT PRIMARY KEY,
                hrv_7d_avg REAL,
                hrv_30d_avg REAL,
                rhr_7d_avg REAL,
                rhr_30d_avg REAL,
                sleep_7d_avg REAL,
                sleep_30d_avg REAL,
                strain_7d_avg REAL,
                recovery_7d_avg REAL
            );
        """)
        conn.commit()
        conn.close()

        yield path

        os.unlink(path)

    def test_save_and_load_baselines(self, temp_db):
        """Test saving and loading baselines."""
        baselines = PersonalBaselines(
            date="2024-01-15",
            hrv_7d_avg=52.5,
            hrv_30d_avg=50.0,
            rhr_7d_avg=58.0,
            rhr_30d_avg=59.0,
            sleep_7d_avg=7.25,
            sleep_30d_avg=7.1,
            strain_7d_avg=12.5,
            recovery_7d_avg=68.0,
        )

        save_baselines(temp_db, baselines)
        loaded = get_saved_baselines(temp_db, "2024-01-15")

        assert loaded is not None
        assert loaded.date == "2024-01-15"
        assert loaded.hrv_7d_avg == 52.5
        assert loaded.hrv_30d_avg == 50.0
        assert loaded.rhr_7d_avg == 58.0
        assert loaded.sleep_7d_avg == 7.25
        assert loaded.strain_7d_avg == 12.5
        assert loaded.recovery_7d_avg == 68.0

    def test_load_nonexistent_returns_none(self, temp_db):
        """Test that loading nonexistent date returns None."""
        loaded = get_saved_baselines(temp_db, "2024-01-01")
        assert loaded is None

    def test_save_overwrites_existing(self, temp_db):
        """Test that saving overwrites existing baselines."""
        baselines1 = PersonalBaselines(
            date="2024-01-15",
            hrv_7d_avg=50.0,
        )
        save_baselines(temp_db, baselines1)

        baselines2 = PersonalBaselines(
            date="2024-01-15",
            hrv_7d_avg=55.0,  # Updated value
        )
        save_baselines(temp_db, baselines2)

        loaded = get_saved_baselines(temp_db, "2024-01-15")
        assert loaded is not None
        assert loaded.hrv_7d_avg == 55.0

    def test_get_personal_baselines_with_data(self, temp_db):
        """Test calculating personal baselines from historical data."""
        conn = sqlite3.connect(temp_db)

        # Insert test data for the past 10 days
        base_date = datetime(2024, 1, 15)
        for i in range(10):
            date_str = (base_date - timedelta(days=i)).strftime("%Y-%m-%d")
            conn.execute(
                "INSERT INTO daily_wellness (date, fetched_at) VALUES (?, ?)",
                (date_str, datetime.now().isoformat())
            )
            conn.execute(
                "INSERT INTO hrv_data (date, hrv_last_night_avg) VALUES (?, ?)",
                (date_str, 50 + i)  # 50, 51, 52, ... 59
            )
            conn.execute(
                "INSERT INTO sleep_data (date, total_sleep_seconds) VALUES (?, ?)",
                (date_str, 25200 + i * 360)  # 7h + increments
            )

        conn.commit()
        conn.close()

        baselines = get_personal_baselines(temp_db, "2024-01-15")

        assert baselines is not None
        assert baselines.date == "2024-01-15"
        # Should have calculated averages
        assert baselines.hrv_7d_avg is not None
        assert baselines.sleep_7d_avg is not None


class TestDirectionIndicator:
    """Tests for DirectionIndicator dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        indicator = DirectionIndicator(
            direction='up',
            change_pct=10.5,
            baseline=50.0,
            current=55.25,
        )
        result = indicator.to_dict()
        assert result == {
            'direction': 'up',
            'change_pct': 10.5,
            'baseline': 50.0,
            'current': 55.25,
        }


class TestPersonalBaselines:
    """Tests for PersonalBaselines dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        baselines = PersonalBaselines(
            date="2024-01-15",
            hrv_7d_avg=52.0,
            hrv_30d_avg=50.0,
            sleep_7d_avg=7.5,
        )
        result = baselines.to_dict()
        assert result['date'] == "2024-01-15"
        assert result['hrv_7d_avg'] == 52.0
        assert result['hrv_30d_avg'] == 50.0
        assert result['sleep_7d_avg'] == 7.5
        assert result['rhr_7d_avg'] is None

    def test_default_values(self):
        """Test that default values are None."""
        baselines = PersonalBaselines(date="2024-01-15")
        assert baselines.hrv_7d_avg is None
        assert baselines.hrv_30d_avg is None
        assert baselines.rhr_7d_avg is None
        assert baselines.sleep_7d_avg is None
        assert baselines.strain_7d_avg is None
        assert baselines.recovery_7d_avg is None
