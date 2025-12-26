"""Integration tests for end-to-end functionality."""

import pytest
import sqlite3
import tempfile
import os
from datetime import date, timedelta
from pathlib import Path

from training_analyzer.db.database import TrainingDatabase, ActivityMetrics, DailyFitnessMetrics
from training_analyzer.services.coach import CoachService
from training_analyzer.analysis.trends import calculate_fitness_trend, detect_overtraining_signals
from training_analyzer.analysis.weekly import analyze_week
from training_analyzer.analysis.goals import (
    RaceDistance,
    RaceGoal,
    assess_goal_progress,
    calculate_training_paces,
)


class TestDatabaseIntegration:
    """Integration tests for database operations."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db = TrainingDatabase(db_path)
        yield db

        # Cleanup
        os.unlink(db_path)

    def test_full_activity_workflow(self, temp_db):
        """Test complete activity storage and retrieval workflow."""
        db = temp_db

        # Store activity
        activity = ActivityMetrics(
            activity_id="test-123",
            date=date.today().isoformat(),
            activity_type="running",
            activity_name="Morning Run",
            hrss=75.5,
            trimp=85.0,
            avg_hr=145,
            max_hr=172,
            duration_min=45.0,
            distance_km=8.5,
            pace_sec_per_km=318,
            zone1_pct=10.0,
            zone2_pct=60.0,
            zone3_pct=25.0,
            zone4_pct=5.0,
            zone5_pct=0.0,
        )

        db.save_activity_metrics(activity)

        # Retrieve and verify
        retrieved = db.get_activity_metrics("test-123")
        assert retrieved is not None
        assert retrieved.activity_id == "test-123"
        assert retrieved.hrss == 75.5
        assert retrieved.distance_km == 8.5

    def test_full_fitness_workflow(self, temp_db):
        """Test complete fitness metrics workflow."""
        db = temp_db

        # Store multiple days of fitness data
        for i in range(10):
            day = (date.today() - timedelta(days=9 - i)).isoformat()
            metrics = DailyFitnessMetrics(
                date=day,
                daily_load=50 + i * 5,
                ctl=30 + i * 0.5,
                atl=25 + i * 1.0,
                tsb=5 - i * 0.5,
                acwr=1.0 + i * 0.02,
                risk_zone="optimal" if i < 7 else "caution",
            )
            db.save_fitness_metrics(metrics)

        # Retrieve range
        start = (date.today() - timedelta(days=9)).isoformat()
        end = date.today().isoformat()

        results = db.get_fitness_range(start, end)

        assert len(results) == 10
        assert results[0].date == end  # Should be ordered DESC

    def test_race_goals_workflow(self, temp_db):
        """Test race goals storage and retrieval."""
        db = temp_db

        # Save a goal
        race_date = (date.today() + timedelta(days=90)).isoformat()
        goal_id = db.save_race_goal(
            race_date=race_date,
            distance="21.0975",  # Half marathon
            target_time_sec=6300,  # 1:45:00
            notes="Spring half marathon",
        )

        assert goal_id is not None

        # Retrieve goals
        goals = db.get_race_goals(upcoming_only=True)

        assert len(goals) == 1
        assert goals[0]["target_time_sec"] == 6300

        # Delete goal
        deleted = db.delete_race_goal(goal_id)
        assert deleted is True

        # Verify deleted
        goals = db.get_race_goals()
        assert len(goals) == 0

    def test_weekly_summary_workflow(self, temp_db):
        """Test weekly summary storage and retrieval."""
        db = temp_db
        import json

        week_start = "2024-01-01"

        db.save_weekly_summary(
            week_start=week_start,
            total_distance_km=50.0,
            total_duration_min=300.0,
            total_load=350.0,
            activity_count=5,
            zone_distribution=json.dumps({
                "zone1_pct": 20,
                "zone2_pct": 55,
                "zone3_pct": 15,
                "zone4_pct": 8,
                "zone5_pct": 2,
            }),
            ctl_start=45.0,
            ctl_end=47.5,
            ctl_change=2.5,
            atl_change=5.0,
            week_over_week_change=10.0,
            is_recovery_week=False,
            insights=json.dumps(["Good week", "Consistent training"]),
        )

        # Retrieve
        summary = db.get_weekly_summary(week_start)

        assert summary is not None
        assert summary["total_distance_km"] == 50.0
        assert summary["activity_count"] == 5


class TestCoachServiceIntegration:
    """Integration tests for the coach service."""

    @pytest.fixture
    def coach_with_data(self):
        """Create coach service with test data."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db = TrainingDatabase(db_path)

        # Add test activities
        for i in range(14):
            day = (date.today() - timedelta(days=13 - i)).isoformat()

            activity = ActivityMetrics(
                activity_id=f"act-{i}",
                date=day,
                activity_type="running",
                activity_name=f"Run {i}",
                hrss=60 + (i % 3) * 15,  # Varying load
                trimp=70 + (i % 3) * 20,
                avg_hr=140 + (i % 3) * 5,
                max_hr=170,
                duration_min=40 + (i % 2) * 20,
                distance_km=7 + (i % 2) * 3,
                pace_sec_per_km=330,
                zone1_pct=15,
                zone2_pct=60,
                zone3_pct=20,
                zone4_pct=5,
                zone5_pct=0,
            )
            db.save_activity_metrics(activity)

            fitness = DailyFitnessMetrics(
                date=day,
                daily_load=activity.hrss,
                ctl=35 + i * 0.3,
                atl=30 + i * 0.5,
                tsb=5 - i * 0.2,
                acwr=1.0,
                risk_zone="optimal",
            )
            db.save_fitness_metrics(fitness)

        coach = CoachService(training_db=db)

        yield coach, db

        # Cleanup
        os.unlink(db_path)

    def test_daily_briefing_with_data(self, coach_with_data):
        """Test daily briefing generation with real data."""
        coach, db = coach_with_data

        briefing = coach.get_daily_briefing()

        assert "date" in briefing
        assert "readiness" in briefing
        assert "recommendation" in briefing
        assert "training_status" in briefing

        # Should have training status since we have fitness data
        assert briefing["training_status"] is not None
        assert "ctl" in briefing["training_status"]

    def test_weekly_summary_with_data(self, coach_with_data):
        """Test weekly summary with real data."""
        coach, db = coach_with_data

        summary = coach.get_weekly_summary()

        assert "week_start" in summary
        assert "total_load" in summary
        assert "workout_count" in summary
        assert summary["workout_count"] >= 0


class TestAnalysisPipelineIntegration:
    """Integration tests for the analysis pipeline."""

    @pytest.fixture
    def sample_data(self):
        """Create sample fitness and activity data."""
        # Create 28 days of fitness history
        fitness_history = []
        activities = []
        base_date = date.today() - timedelta(days=28)

        for i in range(28):
            day = base_date + timedelta(days=i)
            day_str = day.isoformat()

            # Improving CTL trend
            fitness_history.append({
                "date": day_str,
                "ctl": 35 + i * 0.4,
                "atl": 30 + (i % 7) * 2,
                "tsb": 5 - (i % 7),
                "acwr": 0.95 + (i % 10) * 0.02,
                "daily_load": 60 + (i % 3) * 20,
            })

            # Add activity every other day
            if i % 2 == 0:
                activities.append({
                    "date": day_str,
                    "activity_type": "running",
                    "hrss": 60 + (i % 4) * 15,
                    "duration_min": 45 + (i % 3) * 15,
                    "distance_km": 8 + (i % 3) * 2,
                    "avg_hr": 140 + (i % 5) * 3,
                    "pace_sec_per_km": 330 - i * 2,  # Improving pace
                    "zone1_pct": 15,
                    "zone2_pct": 55,
                    "zone3_pct": 20,
                    "zone4_pct": 8,
                    "zone5_pct": 2,
                })

        return fitness_history, activities

    def test_full_trend_analysis(self, sample_data):
        """Test complete trend analysis pipeline."""
        fitness_history, activities = sample_data

        # Calculate fitness trend
        trend = calculate_fitness_trend(fitness_history, period_days=28)

        assert trend is not None
        assert trend.trend_direction == "improving"
        assert trend.ctl_end > trend.ctl_start

        # Check for overtraining signals (should be none with this data)
        signals = detect_overtraining_signals(fitness_history, [])
        # This data is designed to be healthy, so minimal signals expected
        assert len([s for s in signals if "danger" in s.lower()]) == 0

    def test_full_weekly_analysis(self, sample_data):
        """Test complete weekly analysis pipeline."""
        fitness_history, activities = sample_data

        # Analyze last week
        week_activities = activities[-7:]
        week_fitness = fitness_history[-7:]

        analysis = analyze_week(week_activities, week_fitness)

        assert analysis.activity_count > 0
        assert analysis.total_load > 0
        # Zone percentages should sum to ~100
        zone_sum = (
            analysis.zone1_pct +
            analysis.zone2_pct +
            analysis.zone3_pct +
            analysis.zone4_pct +
            analysis.zone5_pct
        )
        assert 98 < zone_sum < 102  # Allow for rounding

    def test_goal_assessment_pipeline(self, sample_data):
        """Test goal assessment with real-ish data."""
        fitness_history, activities = sample_data

        # Create a goal
        goal = RaceGoal(
            race_date=date.today() + timedelta(days=60),
            distance=RaceDistance.TEN_K,
            target_time_sec=2400,  # 40 min
        )

        # Get current fitness (use last entry)
        current_fitness = fitness_history[-1]

        # Assess progress
        progress = assess_goal_progress(
            goal=goal,
            current_fitness=current_fitness,
            recent_activities=activities,
        )

        assert progress.weeks_remaining > 0
        assert len(progress.recommendations) > 0
        assert progress.ctl_current > 0


class TestCLICommands:
    """Tests for CLI command execution (without actually invoking CLI)."""

    @pytest.fixture
    def db_with_data(self):
        """Create database with test data for CLI testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db = TrainingDatabase(db_path)

        # Add minimal test data
        today = date.today()
        for i in range(7):
            day = (today - timedelta(days=i)).isoformat()

            activity = ActivityMetrics(
                activity_id=f"cli-test-{i}",
                date=day,
                activity_type="running",
                activity_name=f"Test Run {i}",
                hrss=50.0,
                trimp=60.0,
                avg_hr=140,
                max_hr=165,
                duration_min=40.0,
                distance_km=7.0,
                pace_sec_per_km=342,
                zone1_pct=20,
                zone2_pct=60,
                zone3_pct=15,
                zone4_pct=5,
                zone5_pct=0,
            )
            db.save_activity_metrics(activity)

            fitness = DailyFitnessMetrics(
                date=day,
                daily_load=50.0,
                ctl=40.0,
                atl=35.0,
                tsb=5.0,
                acwr=0.87,
                risk_zone="optimal",
            )
            db.save_fitness_metrics(fitness)

        yield db

        os.unlink(db_path)

    def test_database_has_data_for_cli(self, db_with_data):
        """Verify database has expected data for CLI commands."""
        db = db_with_data

        stats = db.get_stats()
        assert stats["total_activities"] == 7
        assert stats["total_fitness_days"] == 7

    def test_fitness_metrics_retrievable(self, db_with_data):
        """Test that fitness metrics can be retrieved for CLI display."""
        db = db_with_data

        latest = db.get_latest_fitness_metrics()
        assert latest is not None
        assert latest.ctl == 40.0
        assert latest.risk_zone == "optimal"

    def test_activities_retrievable_by_date(self, db_with_data):
        """Test activity retrieval for CLI."""
        db = db_with_data

        today = date.today().isoformat()
        activities = db.get_activities_for_date(today)

        assert len(activities) == 1
        assert activities[0].activity_type == "running"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def empty_db(self):
        """Create empty database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db = TrainingDatabase(db_path)
        yield db
        os.unlink(db_path)

    def test_empty_database_handling(self, empty_db):
        """Test handling of empty database."""
        db = empty_db

        # Should not raise errors
        latest = db.get_latest_fitness_metrics()
        assert latest is None

        activities = db.get_activities_for_date(date.today().isoformat())
        assert activities == []

        stats = db.get_stats()
        assert stats["total_activities"] == 0

    def test_trend_analysis_with_sparse_data(self):
        """Test trend analysis with minimal data."""
        # Only 2 data points
        sparse_history = [
            {"date": date.today().isoformat(), "ctl": 50, "daily_load": 100},
            {"date": (date.today() - timedelta(days=1)).isoformat(), "ctl": 48, "daily_load": 80},
        ]

        trend = calculate_fitness_trend(sparse_history)

        # Should still work with minimal data
        assert trend is not None

    def test_goal_with_no_activities(self):
        """Test goal assessment with no activity data."""
        goal = RaceGoal(
            race_date=date.today() + timedelta(days=30),
            distance=RaceDistance.FIVE_K,
            target_time_sec=1200,
        )

        progress = assess_goal_progress(
            goal=goal,
            current_fitness={"ctl": 30},
            recent_activities=[],
        )

        # Should provide default prediction
        assert progress.current_predicted_time > 0
        assert len(progress.recommendations) > 0

    def test_weekly_analysis_single_activity(self):
        """Test weekly analysis with single activity."""
        activities = [{
            "date": date.today().isoformat(),
            "hrss": 75,
            "duration_min": 60,
            "distance_km": 10,
            "zone1_pct": 20,
            "zone2_pct": 60,
            "zone3_pct": 15,
            "zone4_pct": 5,
            "zone5_pct": 0,
        }]

        analysis = analyze_week(activities, [])

        assert analysis.activity_count == 1
        assert analysis.total_load == 75


class TestDataConsistency:
    """Tests for data consistency across the system."""

    @pytest.fixture
    def populated_db(self):
        """Create database with consistent test data."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db = TrainingDatabase(db_path)

        # Create consistent data for 30 days
        for i in range(30):
            day = (date.today() - timedelta(days=29 - i)).isoformat()

            activity = ActivityMetrics(
                activity_id=f"consistency-{i}",
                date=day,
                activity_type="running",
                activity_name=f"Run {i}",
                hrss=100.0,  # Constant load
                trimp=110.0,
                avg_hr=155,
                max_hr=175,
                duration_min=60.0,
                distance_km=10.0,
                pace_sec_per_km=360,
                zone1_pct=10,
                zone2_pct=50,
                zone3_pct=30,
                zone4_pct=10,
                zone5_pct=0,
            )
            db.save_activity_metrics(activity)

        yield db
        os.unlink(db_path)

    def test_daily_load_aggregation(self, populated_db):
        """Test that daily loads aggregate correctly."""
        db = populated_db

        start = (date.today() - timedelta(days=6)).isoformat()
        end = date.today().isoformat()

        loads = db.get_daily_load_totals(start, end)

        # Should have 7 days
        assert len(loads) == 7

        # Each day should have 100 HRSS
        for load in loads:
            assert load["total_hrss"] == 100.0

    def test_activity_retrieval_consistency(self, populated_db):
        """Test consistency of activity retrieval methods."""
        db = populated_db
        today = date.today().isoformat()

        # Get by date
        by_date = db.get_activities_for_date(today)

        # Get by ID
        by_id = db.get_activity_metrics(by_date[0].activity_id) if by_date else None

        if by_date:
            assert by_id is not None
            assert by_id.hrss == by_date[0].hrss
            assert by_id.date == by_date[0].date
