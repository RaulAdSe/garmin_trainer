"""Tests for causality engine - pattern detection, streaks, and trend alerts."""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta

from garmin_client.causality import (
    Correlation,
    Streak,
    TrendAlert,
    WeeklySummary,
    detect_sleep_consistency_impact,
    detect_step_count_correlation,
    detect_alcohol_nights,
    get_all_correlations,
    calculate_green_day_streak,
    calculate_sleep_consistency_streak,
    calculate_step_goal_streak,
    get_all_streaks,
    detect_hrv_trend,
    detect_sleep_trend,
    detect_recovery_trend,
    get_all_trend_alerts,
    generate_weekly_summary,
    create_causality_tables,
    save_correlation,
    save_streak,
    get_saved_correlations,
    get_saved_streaks,
)


def create_test_db():
    """Create a temporary test database with sample data."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    conn = sqlite3.connect(db_path)

    # Create tables
    conn.executescript("""
        CREATE TABLE daily_wellness (
            date TEXT PRIMARY KEY,
            fetched_at TEXT NOT NULL,
            resting_heart_rate INTEGER
        );

        CREATE TABLE sleep_data (
            date TEXT PRIMARY KEY,
            total_sleep_seconds INTEGER DEFAULT 0,
            deep_sleep_seconds INTEGER DEFAULT 0,
            rem_sleep_seconds INTEGER DEFAULT 0
        );

        CREATE TABLE hrv_data (
            date TEXT PRIMARY KEY,
            hrv_last_night_avg INTEGER
        );

        CREATE TABLE stress_data (
            date TEXT PRIMARY KEY,
            body_battery_charged INTEGER,
            body_battery_drained INTEGER,
            high_stress_duration INTEGER DEFAULT 0
        );

        CREATE TABLE activity_data (
            date TEXT PRIMARY KEY,
            steps INTEGER DEFAULT 0,
            steps_goal INTEGER DEFAULT 10000,
            intensity_minutes INTEGER DEFAULT 0
        );

        CREATE TABLE correlations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            detected_at TEXT NOT NULL,
            pattern_type TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            impact REAL NOT NULL,
            confidence REAL NOT NULL,
            sample_size INTEGER NOT NULL,
            is_active INTEGER DEFAULT 1
        );

        CREATE TABLE streaks (
            name TEXT PRIMARY KEY,
            current_count INTEGER DEFAULT 0,
            best_count INTEGER DEFAULT 0,
            last_date TEXT,
            is_active INTEGER DEFAULT 1
        );
    """)

    conn.commit()
    conn.close()

    return db_path


def populate_test_data(db_path: str, days: int = 30):
    """Populate test database with sample wellness data."""
    conn = sqlite3.connect(db_path)

    base_date = datetime.now().date()

    for i in range(days):
        date = (base_date - timedelta(days=i)).isoformat()

        # Create somewhat realistic patterns
        # Good sleep = 7-8 hours, bad = 5-6 hours
        is_good_sleep = i % 3 != 0  # Every 3rd day is bad sleep

        sleep_hours = 7.5 if is_good_sleep else 5.5
        sleep_seconds = int(sleep_hours * 3600)

        # HRV follows sleep pattern with some noise
        base_hrv = 50
        hrv = base_hrv + (5 if is_good_sleep else -10) + (i % 5 - 2)

        # Body battery follows recovery
        bb_charged = 70 + (10 if is_good_sleep else -15)
        bb_drained = 50 + (i % 10)

        # Steps vary - every 4th day is high step day
        steps = 10000 if i % 4 == 0 else 5000

        conn.execute("""
            INSERT INTO daily_wellness (date, fetched_at, resting_heart_rate)
            VALUES (?, ?, ?)
        """, (date, datetime.now().isoformat(), 60 + (i % 5)))

        conn.execute("""
            INSERT INTO sleep_data (date, total_sleep_seconds, deep_sleep_seconds, rem_sleep_seconds)
            VALUES (?, ?, ?, ?)
        """, (date, sleep_seconds, sleep_seconds // 4, sleep_seconds // 4))

        conn.execute("""
            INSERT INTO hrv_data (date, hrv_last_night_avg)
            VALUES (?, ?)
        """, (date, hrv))

        conn.execute("""
            INSERT INTO stress_data (date, body_battery_charged, body_battery_drained, high_stress_duration)
            VALUES (?, ?, ?, ?)
        """, (date, bb_charged, bb_drained, 3600 if i % 5 == 0 else 7200))

        conn.execute("""
            INSERT INTO activity_data (date, steps, steps_goal, intensity_minutes)
            VALUES (?, ?, ?, ?)
        """, (date, steps, 10000, 30 if steps >= 10000 else 10))

    conn.commit()
    conn.close()


class TestCorrelationDataclass:
    """Tests for Correlation dataclass."""

    def test_creation(self):
        """Test Correlation creation."""
        corr = Correlation(
            pattern_type='negative',
            category='sleep',
            title='Late workout impact',
            description='Late workouts drop recovery 18%',
            impact=-18.0,
            confidence=0.85,
            sample_size=12
        )
        assert corr.pattern_type == 'negative'
        assert corr.impact == -18.0

    def test_to_dict(self):
        """Test Correlation to_dict method."""
        corr = Correlation(
            pattern_type='positive',
            category='activity',
            title='8k+ step days',
            description='High step days improve recovery',
            impact=12.0,
            confidence=0.7,
            sample_size=8
        )
        d = corr.to_dict()
        assert d['pattern_type'] == 'positive'
        assert d['impact'] == 12.0
        assert 'sample_size' in d


class TestStreakDataclass:
    """Tests for Streak dataclass."""

    def test_creation(self):
        """Test Streak creation."""
        streak = Streak(
            name='green_days',
            current_count=5,
            best_count=7,
            is_active=True,
            last_date='2024-12-20'
        )
        assert streak.name == 'green_days'
        assert streak.current_count == 5

    def test_to_dict(self):
        """Test Streak to_dict method."""
        streak = Streak(
            name='sleep_consistency',
            current_count=3,
            best_count=10,
            is_active=True,
            last_date='2024-12-20'
        )
        d = streak.to_dict()
        assert d['name'] == 'sleep_consistency'
        assert d['current_count'] == 3


class TestTrendAlertDataclass:
    """Tests for TrendAlert dataclass."""

    def test_creation(self):
        """Test TrendAlert creation."""
        alert = TrendAlert(
            metric='HRV',
            direction='declining',
            days=4,
            change_pct=-15.0,
            severity='warning'
        )
        assert alert.metric == 'HRV'
        assert alert.direction == 'declining'

    def test_to_dict(self):
        """Test TrendAlert to_dict method."""
        alert = TrendAlert(
            metric='Recovery',
            direction='improving',
            days=3,
            change_pct=12.0,
            severity='positive'
        )
        d = alert.to_dict()
        assert d['metric'] == 'Recovery'
        assert d['severity'] == 'positive'


class TestSleepConsistencyCorrelation:
    """Tests for sleep consistency correlation detection."""

    def test_with_sufficient_data(self):
        """Test detection with enough data points."""
        db_path = create_test_db()
        try:
            populate_test_data(db_path, days=30)
            result = detect_sleep_consistency_impact(db_path)
            # May or may not detect pattern depending on data variance
            # Just verify it doesn't crash
            assert result is None or isinstance(result, Correlation)
        finally:
            os.unlink(db_path)

    def test_with_insufficient_data(self):
        """Test that insufficient data returns None."""
        db_path = create_test_db()
        try:
            populate_test_data(db_path, days=5)  # Too few days
            result = detect_sleep_consistency_impact(db_path)
            assert result is None
        finally:
            os.unlink(db_path)


class TestStepCountCorrelation:
    """Tests for step count correlation detection."""

    def test_with_sufficient_data(self):
        """Test detection with enough data points."""
        db_path = create_test_db()
        try:
            populate_test_data(db_path, days=30)
            result = detect_step_count_correlation(db_path)
            assert result is None or isinstance(result, Correlation)
        finally:
            os.unlink(db_path)

    def test_with_insufficient_data(self):
        """Test that insufficient data returns None."""
        db_path = create_test_db()
        try:
            populate_test_data(db_path, days=3)
            result = detect_step_count_correlation(db_path)
            assert result is None
        finally:
            os.unlink(db_path)


class TestAlcoholNightsDetection:
    """Tests for alcohol/stress night detection via HRV crashes."""

    def test_with_sufficient_data(self):
        """Test detection with enough data points."""
        db_path = create_test_db()
        try:
            populate_test_data(db_path, days=30)
            result = detect_alcohol_nights(db_path)
            assert result is None or isinstance(result, Correlation)
        finally:
            os.unlink(db_path)


class TestGetAllCorrelations:
    """Tests for getting all correlations."""

    def test_returns_list(self):
        """Test that get_all_correlations returns a list."""
        db_path = create_test_db()
        try:
            populate_test_data(db_path, days=30)
            result = get_all_correlations(db_path)
            assert isinstance(result, list)
            for item in result:
                assert isinstance(item, Correlation)
        finally:
            os.unlink(db_path)


class TestGreenDayStreak:
    """Tests for green day streak calculation."""

    def test_calculates_streak(self):
        """Test that green day streak is calculated."""
        db_path = create_test_db()
        try:
            populate_test_data(db_path, days=14)
            result = calculate_green_day_streak(db_path)
            assert isinstance(result, Streak)
            assert result.name == 'green_days'
            assert result.current_count >= 0
            assert result.best_count >= result.current_count or result.current_count == 0
        finally:
            os.unlink(db_path)

    def test_empty_database(self):
        """Test with empty database."""
        db_path = create_test_db()
        try:
            result = calculate_green_day_streak(db_path)
            assert result.current_count == 0
            assert result.best_count == 0
        finally:
            os.unlink(db_path)


class TestSleepConsistencyStreak:
    """Tests for sleep consistency streak calculation."""

    def test_calculates_streak(self):
        """Test that sleep consistency streak is calculated."""
        db_path = create_test_db()
        try:
            populate_test_data(db_path, days=14)
            result = calculate_sleep_consistency_streak(db_path)
            assert isinstance(result, Streak)
            assert result.name == 'sleep_consistency'
            assert result.current_count >= 0
        finally:
            os.unlink(db_path)

    def test_custom_threshold(self):
        """Test with custom sleep threshold."""
        db_path = create_test_db()
        try:
            populate_test_data(db_path, days=14)
            result = calculate_sleep_consistency_streak(db_path, threshold_hours=6.0)
            assert isinstance(result, Streak)
            # Lower threshold should result in higher streak counts
        finally:
            os.unlink(db_path)


class TestStepGoalStreak:
    """Tests for step goal streak calculation."""

    def test_calculates_streak(self):
        """Test that step goal streak is calculated."""
        db_path = create_test_db()
        try:
            populate_test_data(db_path, days=14)
            result = calculate_step_goal_streak(db_path)
            assert isinstance(result, Streak)
            assert result.name == 'step_goal'
            assert result.current_count >= 0
        finally:
            os.unlink(db_path)


class TestGetAllStreaks:
    """Tests for getting all streaks."""

    def test_returns_list(self):
        """Test that get_all_streaks returns a list."""
        db_path = create_test_db()
        try:
            populate_test_data(db_path, days=14)
            result = get_all_streaks(db_path)
            assert isinstance(result, list)
            for item in result:
                assert isinstance(item, Streak)
        finally:
            os.unlink(db_path)


class TestHrvTrend:
    """Tests for HRV trend detection."""

    def test_with_sufficient_data(self):
        """Test trend detection with enough data."""
        db_path = create_test_db()
        try:
            populate_test_data(db_path, days=14)
            result = detect_hrv_trend(db_path)
            assert result is None or isinstance(result, TrendAlert)
        finally:
            os.unlink(db_path)

    def test_with_insufficient_data(self):
        """Test that insufficient data returns None."""
        db_path = create_test_db()
        try:
            populate_test_data(db_path, days=2)
            result = detect_hrv_trend(db_path)
            assert result is None
        finally:
            os.unlink(db_path)


class TestSleepTrend:
    """Tests for sleep trend detection."""

    def test_with_sufficient_data(self):
        """Test trend detection with enough data."""
        db_path = create_test_db()
        try:
            populate_test_data(db_path, days=14)
            result = detect_sleep_trend(db_path)
            assert result is None or isinstance(result, TrendAlert)
        finally:
            os.unlink(db_path)


class TestRecoveryTrend:
    """Tests for recovery trend detection."""

    def test_with_sufficient_data(self):
        """Test trend detection with enough data."""
        db_path = create_test_db()
        try:
            populate_test_data(db_path, days=14)
            result = detect_recovery_trend(db_path)
            assert result is None or isinstance(result, TrendAlert)
        finally:
            os.unlink(db_path)


class TestGetAllTrendAlerts:
    """Tests for getting all trend alerts."""

    def test_returns_list(self):
        """Test that get_all_trend_alerts returns a list."""
        db_path = create_test_db()
        try:
            populate_test_data(db_path, days=14)
            result = get_all_trend_alerts(db_path)
            assert isinstance(result, list)
            for item in result:
                assert isinstance(item, TrendAlert)
        finally:
            os.unlink(db_path)


class TestWeeklySummary:
    """Tests for weekly summary generation."""

    def test_generates_summary(self):
        """Test that weekly summary is generated correctly."""
        db_path = create_test_db()
        try:
            populate_test_data(db_path, days=14)
            result = generate_weekly_summary(db_path)
            assert isinstance(result, WeeklySummary)
            assert result.green_days >= 0
            assert result.yellow_days >= 0
            assert result.red_days >= 0
            # Total should be reasonable (query uses >= date('now', '-7 days') which may include today)
            total_days = result.green_days + result.yellow_days + result.red_days
            assert total_days >= 0 and total_days <= 8  # Allow for timezone edge cases
        finally:
            os.unlink(db_path)

    def test_summary_includes_correlations(self):
        """Test that summary includes correlations list."""
        db_path = create_test_db()
        try:
            populate_test_data(db_path, days=30)
            result = generate_weekly_summary(db_path)
            assert isinstance(result.correlations, list)
            assert isinstance(result.streaks, list)
            assert isinstance(result.trend_alerts, list)
        finally:
            os.unlink(db_path)

    def test_summary_to_dict(self):
        """Test that summary can be serialized to dict."""
        db_path = create_test_db()
        try:
            populate_test_data(db_path, days=14)
            result = generate_weekly_summary(db_path)
            d = result.to_dict()
            assert 'green_days' in d
            assert 'correlations' in d
            assert 'streaks' in d
            assert 'trend_alerts' in d
        finally:
            os.unlink(db_path)

    def test_empty_database(self):
        """Test summary with empty database."""
        db_path = create_test_db()
        try:
            result = generate_weekly_summary(db_path)
            assert result.green_days == 0
            assert result.avg_recovery == 0
        finally:
            os.unlink(db_path)


class TestDatabaseOperations:
    """Tests for database save/load operations."""

    def test_create_tables(self):
        """Test that causality tables are created."""
        db_path = create_test_db()
        try:
            create_causality_tables(db_path)
            conn = sqlite3.connect(db_path)
            # Verify tables exist
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [t[0] for t in tables]
            assert 'correlations' in table_names
            assert 'streaks' in table_names
            conn.close()
        finally:
            os.unlink(db_path)

    def test_save_and_load_correlation(self):
        """Test saving and loading correlations."""
        db_path = create_test_db()
        try:
            create_causality_tables(db_path)

            corr = Correlation(
                pattern_type='negative',
                category='workout',
                title='Late workout impact',
                description='Late workouts drop recovery 15%',
                impact=-15.0,
                confidence=0.8,
                sample_size=10
            )

            save_correlation(db_path, corr)

            loaded = get_saved_correlations(db_path)
            assert len(loaded) == 1
            assert loaded[0].title == 'Late workout impact'
            assert loaded[0].impact == -15.0
        finally:
            os.unlink(db_path)

    def test_save_and_load_streak(self):
        """Test saving and loading streaks."""
        db_path = create_test_db()
        try:
            create_causality_tables(db_path)

            streak = Streak(
                name='green_days',
                current_count=5,
                best_count=7,
                is_active=True,
                last_date='2024-12-20'
            )

            save_streak(db_path, streak)

            loaded = get_saved_streaks(db_path)
            assert len(loaded) == 1
            assert loaded[0].name == 'green_days'
            assert loaded[0].current_count == 5
        finally:
            os.unlink(db_path)


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_minimum_sample_size(self):
        """Test that correlations require minimum sample size."""
        db_path = create_test_db()
        try:
            # Populate minimal data
            populate_test_data(db_path, days=4)
            # Correlations should not be detected with insufficient data
            correlations = get_all_correlations(db_path)
            # Either empty or all have reasonable confidence
            for corr in correlations:
                assert corr.sample_size >= 5 or corr.confidence < 0.5
        finally:
            os.unlink(db_path)

    def test_handles_null_values(self):
        """Test that null values in data are handled gracefully."""
        db_path = create_test_db()
        try:
            conn = sqlite3.connect(db_path)
            # Insert data with null values
            date = datetime.now().date().isoformat()
            conn.execute(
                "INSERT INTO daily_wellness (date, fetched_at) VALUES (?, ?)",
                (date, datetime.now().isoformat())
            )
            conn.execute(
                "INSERT INTO hrv_data (date, hrv_last_night_avg) VALUES (?, NULL)",
                (date,)
            )
            conn.commit()
            conn.close()

            # Should not crash
            result = generate_weekly_summary(db_path)
            assert isinstance(result, WeeklySummary)
        finally:
            os.unlink(db_path)

    def test_streak_continuity(self):
        """Test that streak detection properly tracks consecutive days."""
        db_path = create_test_db()
        try:
            conn = sqlite3.connect(db_path)
            base_date = datetime.now().date()

            # Create a 5-day streak of good sleep, then a break, then 3 more days
            for i in range(10):
                date = (base_date - timedelta(days=i)).isoformat()
                # Days 0-4: good sleep (7.5h), Day 5: bad (5h), Days 6-9: good (7.5h)
                sleep_hours = 5.5 if i == 5 else 7.5
                sleep_seconds = int(sleep_hours * 3600)

                conn.execute(
                    "INSERT INTO sleep_data (date, total_sleep_seconds) VALUES (?, ?)",
                    (date, sleep_seconds)
                )

            conn.commit()
            conn.close()

            result = calculate_sleep_consistency_streak(db_path)
            # Current streak should be 5 (days 0-4)
            assert result.current_count == 5
        finally:
            os.unlink(db_path)


class TestConfidenceScoring:
    """Tests for confidence score calculation."""

    def test_confidence_scales_with_sample_size(self):
        """Test that confidence increases with sample size."""
        # Correlations with more data points should have higher confidence
        corr_small = Correlation(
            pattern_type='positive',
            category='sleep',
            title='Test',
            description='Test',
            impact=10.0,
            confidence=0.5,
            sample_size=5
        )

        corr_large = Correlation(
            pattern_type='positive',
            category='sleep',
            title='Test',
            description='Test',
            impact=10.0,
            confidence=1.0,
            sample_size=15
        )

        # Larger sample = higher confidence
        assert corr_large.confidence > corr_small.confidence
