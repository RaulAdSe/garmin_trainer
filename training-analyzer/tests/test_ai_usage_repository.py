"""Tests for AIUsageRepository - Usage logging, cost calculation, and rate limiting.

This module tests:
1. AI request logging (start and complete patterns)
2. Cost calculation from model pricing
3. Usage summaries and aggregations
4. Rate limiting with usage limits
5. Usage history by date range and analysis type
6. Model pricing integration
"""

import os
import pytest
import tempfile
import uuid
from datetime import datetime, date, timedelta
from pathlib import Path

from training_analyzer.db.repositories.ai_usage_repository import (
    AIUsageRepository,
    AIUsageLog,
    UsageSummary,
    UsageLimits,
    get_ai_usage_repository,
)


@pytest.fixture
def temp_db_path():
    """Create a temporary database file path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def ai_repo(temp_db_path):
    """Create an AIUsageRepository with a temporary database."""
    return AIUsageRepository(db_path=temp_db_path)


@pytest.fixture
def sample_log(ai_repo):
    """Create a sample usage log entry."""
    return ai_repo.log_usage(
        request_id=str(uuid.uuid4()),
        user_id="test-user-123",
        model_id="gpt-4o-mini",
        input_tokens=100,
        output_tokens=50,
        total_cost_cents=0,  # Will be calculated
        analysis_type="workout_analysis",
        duration_ms=500,
    )


class TestAIUsageRepositoryInit:
    """Tests for repository initialization."""

    def test_creates_ai_usage_logs_table(self, ai_repo):
        """ai_usage_logs table should be created on init."""
        with ai_repo._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='ai_usage_logs'"
            )
            result = cursor.fetchone()
            assert result is not None

    def test_creates_ai_model_pricing_table(self, ai_repo):
        """ai_model_pricing table should be created on init."""
        with ai_repo._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='ai_model_pricing'"
            )
            result = cursor.fetchone()
            assert result is not None

    def test_creates_indexes(self, ai_repo):
        """Required indexes should be created."""
        with ai_repo._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_ai_usage_%'"
            )
            indexes = {row["name"] for row in cursor.fetchall()}

            assert "idx_ai_usage_user" in indexes
            assert "idx_ai_usage_created" in indexes
            assert "idx_ai_usage_type" in indexes

    def test_inserts_default_pricing(self, ai_repo):
        """Default model pricing should be inserted."""
        with ai_repo._get_connection() as conn:
            cursor = conn.execute(
                "SELECT model_id FROM ai_model_pricing WHERE provider = 'openai'"
            )
            models = {row["model_id"] for row in cursor.fetchall()}

            assert "gpt-4o-mini" in models
            assert "gpt-4o" in models


class TestRequestLogging:
    """Tests for AI request logging (async pattern)."""

    def test_log_request_creates_pending(self, ai_repo):
        """log_request should create a pending log entry."""
        request_id = str(uuid.uuid4())

        log = ai_repo.log_request(
            request_id=request_id,
            user_id="user-001",
            model_id="gpt-4o-mini",
            analysis_type="chat",
            provider="openai",
            model_type="fast",
            entity_type="workout",
            entity_id="workout-123",
        )

        assert log.request_id == request_id
        assert log.user_id == "user-001"
        assert log.status == "pending"
        assert log.model_id == "gpt-4o-mini"
        assert log.analysis_type == "chat"
        assert log.completed_at is None

    def test_update_request_completes(self, ai_repo):
        """update_request should complete the log entry."""
        request_id = str(uuid.uuid4())

        ai_repo.log_request(
            request_id=request_id,
            user_id="user-001",
            model_id="gpt-4o-mini",
            analysis_type="workout_analysis",
        )

        updated = ai_repo.update_request(
            request_id=request_id,
            status="completed",
            input_tokens=100,
            output_tokens=50,
        )

        assert updated is not None
        assert updated.status == "completed"
        assert updated.input_tokens == 100
        assert updated.output_tokens == 50
        assert updated.completed_at is not None
        assert updated.duration_ms is not None

    def test_update_request_with_error(self, ai_repo):
        """update_request should handle failed requests."""
        request_id = str(uuid.uuid4())

        ai_repo.log_request(
            request_id=request_id,
            user_id="user-001",
            model_id="gpt-4o",
            analysis_type="plan",
        )

        updated = ai_repo.update_request(
            request_id=request_id,
            status="failed",
            error_message="API rate limit exceeded",
        )

        assert updated is not None
        assert updated.status == "failed"
        assert updated.error_message == "API rate limit exceeded"

    def test_update_request_not_found(self, ai_repo):
        """update_request should return None for unknown request."""
        result = ai_repo.update_request(
            request_id="nonexistent-request",
            status="completed",
        )
        assert result is None


class TestUsageLogging:
    """Tests for complete usage logging (single-call pattern)."""

    def test_log_usage_complete(self, ai_repo):
        """log_usage should create complete log entry."""
        request_id = str(uuid.uuid4())

        log = ai_repo.log_usage(
            request_id=request_id,
            user_id="user-001",
            model_id="gpt-4o-mini",
            input_tokens=500,
            output_tokens=200,
            total_cost_cents=0,  # Will be calculated
            analysis_type="workout_analysis",
            duration_ms=1500,
            model_type="fast",
            entity_type="workout",
            entity_id="workout-456",
        )

        assert log.request_id == request_id
        assert log.user_id == "user-001"
        assert log.status == "completed"
        assert log.input_tokens == 500
        assert log.output_tokens == 200
        assert log.duration_ms == 1500

    def test_log_usage_calculates_cost(self, ai_repo):
        """log_usage should calculate cost from pricing table."""
        log = ai_repo.log_usage(
            request_id=str(uuid.uuid4()),
            user_id="user-001",
            model_id="gpt-4o-mini",
            input_tokens=1_000_000,  # 1M tokens
            output_tokens=1_000_000,
            total_cost_cents=0,
            analysis_type="chat",
        )

        # gpt-4o-mini: 15 cents/M input, 60 cents/M output
        expected_input_cost = 15.0  # cents
        expected_output_cost = 60.0  # cents

        assert log.input_cost_cents == pytest.approx(expected_input_cost)
        assert log.output_cost_cents == pytest.approx(expected_output_cost)
        assert log.total_cost_cents == pytest.approx(expected_input_cost + expected_output_cost)

    def test_log_usage_with_cache(self, ai_repo):
        """log_usage should handle cached responses."""
        log = ai_repo.log_usage(
            request_id=str(uuid.uuid4()),
            user_id="user-001",
            model_id="gpt-4o-mini",
            input_tokens=0,
            output_tokens=0,
            total_cost_cents=0,
            analysis_type="workout_analysis",
            is_cached=True,
        )

        assert log.is_cached is True
        assert log.total_cost_cents == 0

    def test_log_usage_default_user(self, ai_repo):
        """log_usage should use default user when None provided."""
        log = ai_repo.log_usage(
            request_id=str(uuid.uuid4()),
            user_id=None,
            model_id="gpt-4o-mini",
            input_tokens=100,
            output_tokens=50,
            total_cost_cents=0,
            analysis_type="chat",
        )

        assert log.user_id == "default"


class TestCostCalculation:
    """Tests for cost calculation from model pricing."""

    def test_calculate_cost_gpt4o_mini(self, ai_repo):
        """Should calculate correct cost for gpt-4o-mini."""
        with ai_repo._get_connection() as conn:
            input_cost, output_cost = ai_repo._calculate_cost(
                conn,
                provider="openai",
                model_id="gpt-4o-mini",
                input_tokens=1_000_000,
                output_tokens=500_000,
            )

        # gpt-4o-mini: 15 cents/M input, 60 cents/M output
        assert input_cost == pytest.approx(15.0)
        assert output_cost == pytest.approx(30.0)  # 0.5M * 60

    def test_calculate_cost_gpt4o(self, ai_repo):
        """Should calculate correct cost for gpt-4o."""
        with ai_repo._get_connection() as conn:
            input_cost, output_cost = ai_repo._calculate_cost(
                conn,
                provider="openai",
                model_id="gpt-4o",
                input_tokens=1_000_000,
                output_tokens=1_000_000,
            )

        # gpt-4o: 250 cents/M input, 1000 cents/M output
        assert input_cost == pytest.approx(250.0)
        assert output_cost == pytest.approx(1000.0)

    def test_calculate_cost_unknown_model(self, ai_repo):
        """Should return zero cost for unknown model."""
        with ai_repo._get_connection() as conn:
            input_cost, output_cost = ai_repo._calculate_cost(
                conn,
                provider="unknown",
                model_id="unknown-model",
                input_tokens=1_000_000,
                output_tokens=1_000_000,
            )

        assert input_cost == 0.0
        assert output_cost == 0.0


class TestUsageSummary:
    """Tests for usage summary and aggregations."""

    @pytest.fixture
    def multiple_logs(self, ai_repo):
        """Create multiple log entries for testing summaries."""
        logs = []
        for i in range(5):
            log = ai_repo.log_usage(
                request_id=str(uuid.uuid4()),
                user_id="summary-user",
                model_id="gpt-4o-mini" if i < 3 else "gpt-4o",
                input_tokens=100 * (i + 1),
                output_tokens=50 * (i + 1),
                total_cost_cents=0,
                analysis_type="workout_analysis" if i < 3 else "chat",
            )
            logs.append(log)
        return logs

    def test_get_usage_summary(self, ai_repo, multiple_logs):
        """Should return aggregated usage summary."""
        summary = ai_repo.get_usage_summary("summary-user")

        assert summary.user_id == "summary-user"
        assert summary.total_requests == 5
        assert summary.total_input_tokens > 0
        assert summary.total_output_tokens > 0
        assert summary.total_tokens == summary.total_input_tokens + summary.total_output_tokens

    def test_get_usage_summary_by_type(self, ai_repo, multiple_logs):
        """Summary should include breakdown by analysis type."""
        summary = ai_repo.get_usage_summary("summary-user")

        assert "workout_analysis" in summary.by_analysis_type
        assert "chat" in summary.by_analysis_type
        assert summary.by_analysis_type["workout_analysis"] == 3
        assert summary.by_analysis_type["chat"] == 2

    def test_get_usage_summary_by_model(self, ai_repo, multiple_logs):
        """Summary should include breakdown by model."""
        summary = ai_repo.get_usage_summary("summary-user")

        assert "gpt-4o-mini" in summary.by_model
        assert "gpt-4o" in summary.by_model

    def test_get_usage_summary_date_range(self, ai_repo, multiple_logs):
        """Summary should respect date range."""
        # Default should be current month
        summary = ai_repo.get_usage_summary("summary-user")
        assert summary.period_start == date.today().replace(day=1)
        assert summary.period_end == date.today()

    def test_get_usage_summary_no_data(self, ai_repo):
        """Summary should handle user with no data."""
        summary = ai_repo.get_usage_summary("no-data-user")

        assert summary.total_requests == 0
        assert summary.total_tokens == 0
        assert summary.total_cost_cents == 0


class TestUsageHistory:
    """Tests for usage history queries."""

    @pytest.fixture
    def logs_for_history(self, ai_repo):
        """Create logs for history testing."""
        for i in range(10):
            ai_repo.log_usage(
                request_id=str(uuid.uuid4()),
                user_id="history-user",
                model_id="gpt-4o-mini",
                input_tokens=100,
                output_tokens=50,
                total_cost_cents=0,
                analysis_type="workout_analysis" if i % 2 == 0 else "chat",
            )

    def test_get_usage_by_date_range(self, ai_repo, logs_for_history):
        """Should get daily usage breakdown."""
        today = date.today()
        history = ai_repo.get_usage_by_date_range(
            "history-user",
            start_date=today - timedelta(days=7),
            end_date=today,
        )

        assert len(history) >= 1
        assert all("date" in entry for entry in history)
        assert all("requests" in entry for entry in history)
        assert all("tokens" in entry for entry in history)
        assert all("cost_usd" in entry for entry in history)

    def test_get_usage_by_analysis_type(self, ai_repo, logs_for_history):
        """Should get usage breakdown by analysis type."""
        breakdown = ai_repo.get_usage_by_analysis_type("history-user", days=30)

        assert len(breakdown) >= 1
        for entry in breakdown:
            assert "analysis_type" in entry
            assert "requests" in entry
            assert "cost_usd" in entry

    def test_get_usage_history_by_granularity(self, ai_repo, logs_for_history):
        """Should support different granularities."""
        # Day granularity
        day_history = ai_repo.get_usage_history("history-user", days=30, granularity="day")
        assert len(day_history) >= 1

        # Week granularity
        week_history = ai_repo.get_usage_history("history-user", days=30, granularity="week")
        assert len(week_history) >= 1

        # Month granularity
        month_history = ai_repo.get_usage_history("history-user", days=30, granularity="month")
        assert len(month_history) >= 1

    def test_get_total_cost(self, ai_repo, logs_for_history):
        """Should calculate total cost in USD."""
        cost = ai_repo.get_total_cost("history-user")
        assert cost >= 0  # Cost should be non-negative


class TestUsageLimits:
    """Tests for rate limiting and usage limits."""

    @pytest.fixture
    def user_with_usage(self, ai_repo):
        """Create user with some usage."""
        user_id = "limit-test-user"
        for i in range(10):
            ai_repo.log_usage(
                request_id=str(uuid.uuid4()),
                user_id=user_id,
                model_id="gpt-4o-mini",
                input_tokens=1000,
                output_tokens=500,
                total_cost_cents=0,
                analysis_type="chat",
            )
        return user_id

    def test_get_usage_limits(self, ai_repo, user_with_usage):
        """Should return current usage against limits."""
        limits = ai_repo.get_usage_limits(
            user_with_usage,
            daily_request_limit=100,
            daily_cost_limit_cents=500,
            monthly_cost_limit_cents=5000,
        )

        assert limits.user_id == user_with_usage
        assert limits.daily_request_limit == 100
        assert limits.current_daily_requests == 10
        assert limits.current_daily_cost_cents >= 0

    def test_is_rate_limited_false(self, ai_repo, user_with_usage):
        """Should not be rate limited when under limits."""
        limits = ai_repo.get_usage_limits(
            user_with_usage,
            daily_request_limit=100,
            daily_cost_limit_cents=50000,
            monthly_cost_limit_cents=500000,
        )

        assert limits.is_rate_limited is False

    def test_is_rate_limited_by_requests(self, ai_repo, user_with_usage):
        """Should be rate limited when exceeding request limit."""
        limits = ai_repo.get_usage_limits(
            user_with_usage,
            daily_request_limit=5,  # Below current 10 requests
            daily_cost_limit_cents=50000,
            monthly_cost_limit_cents=500000,
        )

        assert limits.is_rate_limited is True


class TestRecentLogs:
    """Tests for recent log retrieval."""

    def test_get_recent_logs(self, ai_repo):
        """Should return recent usage logs."""
        # Create some logs
        for i in range(5):
            ai_repo.log_usage(
                request_id=str(uuid.uuid4()),
                user_id="recent-logs-user",
                model_id="gpt-4o-mini",
                input_tokens=100,
                output_tokens=50,
                total_cost_cents=0,
                analysis_type="chat",
            )

        logs = ai_repo.get_recent_logs("recent-logs-user", limit=10)

        assert len(logs) == 5
        assert all(isinstance(log, AIUsageLog) for log in logs)

    def test_get_recent_logs_limit(self, ai_repo):
        """Should respect limit parameter."""
        for i in range(10):
            ai_repo.log_usage(
                request_id=str(uuid.uuid4()),
                user_id="limit-logs-user",
                model_id="gpt-4o-mini",
                input_tokens=100,
                output_tokens=50,
                total_cost_cents=0,
                analysis_type="chat",
            )

        logs = ai_repo.get_recent_logs("limit-logs-user", limit=3)

        assert len(logs) == 3

    def test_get_recent_logs_ordered(self, ai_repo):
        """Logs should be ordered by created_at descending."""
        for i in range(5):
            ai_repo.log_usage(
                request_id=str(uuid.uuid4()),
                user_id="ordered-logs-user",
                model_id="gpt-4o-mini",
                input_tokens=100,
                output_tokens=50,
                total_cost_cents=0,
                analysis_type="chat",
            )

        logs = ai_repo.get_recent_logs("ordered-logs-user", limit=10)

        for i in range(len(logs) - 1):
            assert logs[i].created_at >= logs[i + 1].created_at


class TestDataclasses:
    """Tests for AI usage dataclasses."""

    def test_ai_usage_log_defaults(self):
        """AIUsageLog should have sensible defaults."""
        log = AIUsageLog()

        assert log.id is None
        assert log.user_id == "default"
        assert log.provider == "openai"
        assert log.input_tokens == 0
        assert log.output_tokens == 0
        assert log.total_cost_cents == 0.0
        assert log.status == "completed"
        assert log.is_cached is False

    def test_ai_usage_log_total_tokens(self):
        """total_tokens property should sum input and output."""
        log = AIUsageLog(input_tokens=100, output_tokens=50)
        assert log.total_tokens == 150

    def test_usage_summary_defaults(self):
        """UsageSummary should have sensible defaults."""
        summary = UsageSummary()

        assert summary.total_requests == 0
        assert summary.total_tokens == 0
        assert summary.total_cost_cents == 0.0

    def test_usage_limits_defaults(self):
        """UsageLimits should have sensible defaults."""
        limits = UsageLimits(user_id="test")

        assert limits.daily_request_limit == 100
        assert limits.daily_token_limit == 500000
        assert limits.daily_cost_limit_cents == 500
        assert limits.monthly_cost_limit_cents == 5000
        assert limits.is_rate_limited is False


class TestSingletonPattern:
    """Tests for singleton repository pattern."""

    def test_get_ai_usage_repository_returns_singleton(self, monkeypatch):
        """get_ai_usage_repository should return same instance."""
        from training_analyzer.db.repositories import ai_usage_repository
        monkeypatch.setattr(ai_usage_repository, "_ai_usage_repository", None)

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            monkeypatch.setenv("TRAINING_DB_PATH", temp_path)

            repo1 = get_ai_usage_repository()
            repo2 = get_ai_usage_repository()

            assert repo1 is repo2
        finally:
            monkeypatch.setattr(ai_usage_repository, "_ai_usage_repository", None)
            try:
                os.unlink(temp_path)
            except OSError:
                pass
