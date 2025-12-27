"""Tests for previous day activity feature in workout analysis.

This module tests the new functionality that adds previous day activity data
(steps, active minutes) to the athlete context for LLM analysis.
"""

import pytest
from datetime import date, timedelta

from training_analyzer.models.analysis import AthleteContext
from training_analyzer.llm.context_builder import (
    build_athlete_context_prompt,
    _classify_activity_level,
)
from training_analyzer.agents.analysis_agent import build_athlete_context_from_briefing


# ============================================================================
# Activity Level Classification Tests
# ============================================================================

class TestActivityLevelClassification:
    """Tests for activity level classification based on step count."""

    def test_low_activity_level(self):
        """Test LOW classification for steps < 5000."""
        assert _classify_activity_level(0) == "LOW - rest day"
        assert _classify_activity_level(2500) == "LOW - rest day"
        assert _classify_activity_level(4999) == "LOW - rest day"

    def test_normal_activity_level(self):
        """Test NORMAL classification for 5000-12000 steps."""
        assert _classify_activity_level(5000) == "NORMAL"
        assert _classify_activity_level(8500) == "NORMAL"
        assert _classify_activity_level(12000) == "NORMAL"

    def test_high_activity_level(self):
        """Test HIGH classification for steps > 12000."""
        assert _classify_activity_level(12001) == "HIGH - very active"
        assert _classify_activity_level(15000) == "HIGH - very active"
        assert _classify_activity_level(25000) == "HIGH - very active"

    def test_none_activity_level(self):
        """Test UNKNOWN classification when steps is None."""
        assert _classify_activity_level(None) == "UNKNOWN"


# ============================================================================
# AthleteContext Previous Day Data Tests
# ============================================================================

class TestAthleteContextPrevDayData:
    """Tests for AthleteContext with previous day activity data."""

    def test_context_includes_prev_day_fields(self):
        """Test that AthleteContext correctly stores prev_day fields."""
        ctx = AthleteContext(
            prev_day_steps=3200,
            prev_day_active_minutes=15,
            prev_day_date="2025-12-26",
        )

        assert ctx.prev_day_steps == 3200
        assert ctx.prev_day_active_minutes == 15
        assert ctx.prev_day_date == "2025-12-26"

    def test_context_default_prev_day_fields(self):
        """Test that prev_day fields default to None."""
        ctx = AthleteContext()

        assert ctx.prev_day_steps is None
        assert ctx.prev_day_active_minutes is None
        assert ctx.prev_day_date is None

    def test_to_prompt_context_with_low_prev_day(self):
        """Test prompt context formatting with LOW previous day activity."""
        ctx = AthleteContext(
            prev_day_steps=3200,
            prev_day_active_minutes=15,
            prev_day_date="2025-12-26",
            avg_daily_steps=12500,
            avg_active_minutes=65,
        )

        prompt = ctx.to_prompt_context()

        assert "DAILY ACTIVITY:" in prompt
        assert "Previous day (2025-12-26): 3,200 steps, 15 active min (LOW - rest day)" in prompt
        assert "7-day average: 12,500 steps/day, 65 active min/day" in prompt

    def test_to_prompt_context_with_normal_prev_day(self):
        """Test prompt context formatting with NORMAL previous day activity."""
        ctx = AthleteContext(
            prev_day_steps=8500,
            prev_day_active_minutes=45,
            prev_day_date="2025-12-26",
            avg_daily_steps=10000,
            avg_active_minutes=50,
        )

        prompt = ctx.to_prompt_context()

        assert "Previous day (2025-12-26): 8,500 steps, 45 active min (NORMAL)" in prompt

    def test_to_prompt_context_with_high_prev_day(self):
        """Test prompt context formatting with HIGH previous day activity."""
        ctx = AthleteContext(
            prev_day_steps=18000,
            prev_day_active_minutes=120,
            prev_day_date="2025-12-26",
            avg_daily_steps=10000,
            avg_active_minutes=50,
        )

        prompt = ctx.to_prompt_context()

        assert "Previous day (2025-12-26): 18,000 steps, 120 active min (HIGH - very active)" in prompt

    def test_to_prompt_context_without_prev_day(self):
        """Test prompt context formatting without previous day data."""
        ctx = AthleteContext(
            avg_daily_steps=12500,
            avg_active_minutes=65,
        )

        prompt = ctx.to_prompt_context()

        assert "DAILY ACTIVITY:" in prompt
        assert "7-day average:" in prompt
        assert "Previous day" not in prompt

    def test_to_prompt_context_with_only_prev_day_steps(self):
        """Test prompt context with only prev_day_steps (no active minutes)."""
        ctx = AthleteContext(
            prev_day_steps=5000,
            prev_day_date="2025-12-26",
        )

        prompt = ctx.to_prompt_context()

        assert "Previous day (2025-12-26): 5,000 steps (NORMAL)" in prompt
        # Should not have active min since it's None
        assert ", active min" not in prompt.split("Previous day")[1].split("\n")[0]


# ============================================================================
# Context Builder Previous Day Data Tests
# ============================================================================

class TestContextBuilderPrevDayData:
    """Tests for build_athlete_context_prompt with previous day data."""

    def test_includes_prev_day_activity(self):
        """Test that context builder includes previous day activity."""
        prompt = build_athlete_context_prompt(
            prev_day_activity={
                "steps": 3200,
                "active_minutes": 15,
                "date": "2025-12-26",
            },
            daily_activity={
                "steps": 12500,
                "active_minutes": 65,
            },
        )

        assert "DAILY ACTIVITY:" in prompt
        assert "Previous day (2025-12-26): 3,200 steps, 15 active min (LOW - rest day)" in prompt
        assert "7-day average:" in prompt

    def test_prev_day_only(self):
        """Test context builder with only previous day data."""
        prompt = build_athlete_context_prompt(
            prev_day_activity={
                "steps": 15000,
                "active_minutes": 90,
                "date": "2025-12-26",
            },
        )

        assert "DAILY ACTIVITY:" in prompt
        assert "Previous day (2025-12-26): 15,000 steps, 90 active min (HIGH - very active)" in prompt

    def test_daily_average_only(self):
        """Test context builder with only daily average data."""
        prompt = build_athlete_context_prompt(
            daily_activity={
                "steps": 10000,
                "active_minutes": 50,
            },
        )

        assert "DAILY ACTIVITY:" in prompt
        assert "7-day average:" in prompt
        assert "Previous day" not in prompt

    def test_no_activity_data(self):
        """Test context builder without any activity data."""
        prompt = build_athlete_context_prompt()

        # Should not include DAILY ACTIVITY section
        assert "DAILY ACTIVITY:" not in prompt

    def test_prev_day_without_date(self):
        """Test context builder with prev_day data but no date."""
        prompt = build_athlete_context_prompt(
            prev_day_activity={
                "steps": 5000,
                "active_minutes": 30,
            },
        )

        # Should still include the data, just without the date label
        assert "Previous day : 5,000 steps, 30 active min (NORMAL)" in prompt


# ============================================================================
# Build Athlete Context From Briefing Tests
# ============================================================================

class TestBuildAthleteContextFromBriefingPrevDay:
    """Tests for build_athlete_context_from_briefing with previous day data."""

    def test_extracts_prev_day_activity(self):
        """Test extraction of previous day activity from briefing."""
        briefing = {
            "training_status": {"ctl": 50.0, "atl": 55.0, "tsb": -5.0},
            "prev_day_activity": {
                "steps": 3500,
                "active_minutes": 20,
                "date": "2025-12-26",
            },
            "daily_activity": {
                "avg_steps": 10000,
                "avg_active_minutes": 60,
            },
        }

        context = build_athlete_context_from_briefing(briefing)

        assert context["prev_day_steps"] == 3500
        assert context["prev_day_active_minutes"] == 20
        assert context["prev_day_date"] == "2025-12-26"
        assert context["avg_daily_steps"] == 10000
        assert context["avg_active_minutes"] == 60

    def test_handles_missing_prev_day_activity(self):
        """Test handling when prev_day_activity is missing."""
        briefing = {
            "training_status": {"ctl": 50.0},
            "daily_activity": {
                "avg_steps": 10000,
                "avg_active_minutes": 60,
            },
        }

        context = build_athlete_context_from_briefing(briefing)

        assert context["prev_day_steps"] is None
        assert context["prev_day_active_minutes"] is None
        assert context["prev_day_date"] is None

    def test_handles_empty_prev_day_activity(self):
        """Test handling when prev_day_activity is empty dict."""
        briefing = {
            "training_status": {"ctl": 50.0},
            "prev_day_activity": {},
        }

        context = build_athlete_context_from_briefing(briefing)

        assert context["prev_day_steps"] is None
        assert context["prev_day_active_minutes"] is None
        assert context["prev_day_date"] is None


# ============================================================================
# Integration Tests
# ============================================================================

class TestPrevDayActivityIntegration:
    """Integration tests for the previous day activity feature."""

    def test_full_athlete_context_with_all_activity_data(self):
        """Test AthleteContext with complete activity data in prompt."""
        ctx = AthleteContext(
            ctl=50.0,
            atl=55.0,
            tsb=-5.0,
            acwr=1.1,
            risk_zone="optimal",
            max_hr=185,
            rest_hr=55,
            threshold_hr=165,
            # 7-day averages
            avg_daily_steps=12000,
            avg_active_minutes=70,
            # Previous day (rest day)
            prev_day_steps=3000,
            prev_day_active_minutes=10,
            prev_day_date="2025-12-26",
        )

        prompt = ctx.to_prompt_context()

        # Verify all sections are present
        assert "CTL: 50.0" in prompt
        assert "ATL: 55.0" in prompt
        assert "DAILY ACTIVITY:" in prompt
        assert "Previous day (2025-12-26): 3,000 steps, 10 active min (LOW - rest day)" in prompt
        assert "7-day average: 12,000 steps/day, 70 active min/day" in prompt

    def test_context_builder_preserves_all_data(self):
        """Test that context builder preserves all activity data."""
        prompt = build_athlete_context_prompt(
            fitness_metrics={
                "ctl": 50.0,
                "atl": 55.0,
                "tsb": -5.0,
                "acwr": 1.1,
                "risk_zone": "optimal",
            },
            prev_day_activity={
                "steps": 20000,
                "active_minutes": 150,
                "date": "2025-12-26",
            },
            daily_activity={
                "steps": 10000,
                "active_minutes": 60,
            },
        )

        # Verify fitness metrics
        assert "CTL (Chronic Training Load): 50.0" in prompt

        # Verify activity data
        assert "Previous day (2025-12-26): 20,000 steps, 150 active min (HIGH - very active)" in prompt
        assert "7-day average: 10,000 steps/day, 60 active min/day" in prompt
