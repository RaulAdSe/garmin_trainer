"""Tests for GarminCredentialsRepository - Credential storage, sync config, and sync history.

This module tests:
1. Credential storage (already encrypted by service layer)
2. Credential retrieval
3. Credential deletion
4. Validation status updates
5. Sync configuration management
6. Sync history tracking
7. Auto-sync user listing

Note: Actual encryption/decryption is handled by the encryption service.
This repository stores pre-encrypted credentials.
"""

import os
import pytest
import tempfile
from datetime import datetime, date, timedelta
from pathlib import Path

from training_analyzer.db.repositories.garmin_credentials_repository import (
    GarminCredentialsRepository,
    GarminCredentials,
    GarminSyncConfig,
    GarminSyncHistory,
    get_garmin_credentials_repository,
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
def garmin_repo(temp_db_path):
    """Create a GarminCredentialsRepository with a temporary database."""
    return GarminCredentialsRepository(db_path=temp_db_path)


@pytest.fixture
def sample_credentials(garmin_repo):
    """Create sample encrypted credentials."""
    return garmin_repo.save_credentials(
        user_id="test-user-123",
        encrypted_email="gAAAAABk_encrypted_email_data",
        encrypted_password="gAAAAABk_encrypted_password_data",
        encryption_key_id="v1",
        garmin_user_id="garmin-12345",
        garmin_display_name="Test Athlete",
    )


class TestGarminCredentialsRepositoryInit:
    """Tests for repository initialization."""

    def test_creates_garmin_credentials_table(self, garmin_repo):
        """garmin_credentials table should be created on init."""
        with garmin_repo._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='garmin_credentials'"
            )
            result = cursor.fetchone()
            assert result is not None

    def test_creates_garmin_sync_config_table(self, garmin_repo):
        """garmin_sync_config table should be created on init."""
        with garmin_repo._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='garmin_sync_config'"
            )
            result = cursor.fetchone()
            assert result is not None

    def test_creates_garmin_sync_history_table(self, garmin_repo):
        """garmin_sync_history table should be created on init."""
        with garmin_repo._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='garmin_sync_history'"
            )
            result = cursor.fetchone()
            assert result is not None

    def test_creates_indexes(self, garmin_repo):
        """Required indexes should be created."""
        with garmin_repo._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
            )
            indexes = {row["name"] for row in cursor.fetchall()}

            assert "idx_garmin_creds_user" in indexes
            assert "idx_sync_history_user" in indexes
            assert "idx_sync_history_started" in indexes


class TestCredentialStorage:
    """Tests for credential storage and retrieval."""

    def test_save_credentials_minimal(self, garmin_repo):
        """Should save credentials with minimal fields."""
        creds = garmin_repo.save_credentials(
            user_id="user-001",
            encrypted_email="encrypted_email",
            encrypted_password="encrypted_password",
        )

        assert creds.user_id == "user-001"
        assert creds.encrypted_email == "encrypted_email"
        assert creds.encrypted_password == "encrypted_password"
        assert creds.encryption_key_id == "v1"
        assert creds.is_valid is True

    def test_save_credentials_with_garmin_info(self, garmin_repo):
        """Should save credentials with Garmin account info."""
        creds = garmin_repo.save_credentials(
            user_id="user-002",
            encrypted_email="encrypted_email",
            encrypted_password="encrypted_password",
            garmin_user_id="garmin-id-123",
            garmin_display_name="Athlete Name",
        )

        assert creds.garmin_user_id == "garmin-id-123"
        assert creds.garmin_display_name == "Athlete Name"

    def test_save_credentials_upsert(self, garmin_repo, sample_credentials):
        """Should update credentials on conflict."""
        # Save updated credentials for same user
        updated = garmin_repo.save_credentials(
            user_id=sample_credentials.user_id,
            encrypted_email="new_encrypted_email",
            encrypted_password="new_encrypted_password",
            encryption_key_id="v2",
        )

        assert updated.encrypted_email == "new_encrypted_email"
        assert updated.encrypted_password == "new_encrypted_password"
        assert updated.encryption_key_id == "v2"
        # Note: The returned object is the newly created one, not from DB
        # To verify preservation, we need to retrieve from DB
        retrieved = garmin_repo.get_credentials(sample_credentials.user_id)
        assert retrieved.garmin_display_name == sample_credentials.garmin_display_name

    def test_get_credentials(self, garmin_repo, sample_credentials):
        """Should retrieve credentials by user ID."""
        creds = garmin_repo.get_credentials(sample_credentials.user_id)

        assert creds is not None
        assert creds.user_id == sample_credentials.user_id
        assert creds.encrypted_email == sample_credentials.encrypted_email
        assert creds.encrypted_password == sample_credentials.encrypted_password

    def test_get_credentials_not_found(self, garmin_repo):
        """Should return None for non-existent user."""
        creds = garmin_repo.get_credentials("nonexistent-user")
        assert creds is None

    def test_delete_credentials(self, garmin_repo, sample_credentials):
        """Should delete credentials."""
        result = garmin_repo.delete_credentials(sample_credentials.user_id)

        assert result is True
        assert garmin_repo.get_credentials(sample_credentials.user_id) is None

    def test_delete_credentials_not_found(self, garmin_repo):
        """Should return False for non-existent user."""
        result = garmin_repo.delete_credentials("nonexistent-user")
        assert result is False

    def test_delete_credentials_removes_sync_config(self, garmin_repo, sample_credentials):
        """Should also delete sync config when deleting credentials."""
        # Create sync config
        garmin_repo.update_sync_config(sample_credentials.user_id, auto_sync_enabled=True)

        # Delete credentials
        garmin_repo.delete_credentials(sample_credentials.user_id)

        # Sync config should be gone too
        config = garmin_repo.get_sync_config(sample_credentials.user_id)
        assert config is None


class TestValidationStatus:
    """Tests for credential validation status updates."""

    def test_update_validation_status_valid(self, garmin_repo, sample_credentials):
        """Should update validation status to valid."""
        result = garmin_repo.update_validation_status(
            sample_credentials.user_id,
            is_valid=True,
            validation_error=None,
        )

        assert result is True

        creds = garmin_repo.get_credentials(sample_credentials.user_id)
        assert creds.is_valid is True
        assert creds.validation_error is None
        assert creds.last_validation_at is not None

    def test_update_validation_status_invalid(self, garmin_repo, sample_credentials):
        """Should update validation status to invalid with error."""
        result = garmin_repo.update_validation_status(
            sample_credentials.user_id,
            is_valid=False,
            validation_error="Invalid credentials",
        )

        assert result is True

        creds = garmin_repo.get_credentials(sample_credentials.user_id)
        assert creds.is_valid is False
        assert creds.validation_error == "Invalid credentials"

    def test_update_validation_status_not_found(self, garmin_repo):
        """Should return False for non-existent user."""
        result = garmin_repo.update_validation_status(
            "nonexistent-user",
            is_valid=False,
        )
        assert result is False


class TestSyncConfiguration:
    """Tests for sync configuration management."""

    def test_get_sync_config_not_found(self, garmin_repo):
        """Should return None when no config exists."""
        config = garmin_repo.get_sync_config("no-config-user")
        assert config is None

    def test_update_sync_config_create_new(self, garmin_repo, sample_credentials):
        """Should create sync config if it doesn't exist."""
        config = garmin_repo.update_sync_config(
            sample_credentials.user_id,
            auto_sync_enabled=True,
            sync_frequency="hourly",
        )

        assert config is not None
        assert config.user_id == sample_credentials.user_id
        assert config.auto_sync_enabled is True
        assert config.sync_frequency == "hourly"

    def test_update_sync_config_defaults(self, garmin_repo):
        """New sync config should have sensible defaults."""
        # Create credentials for a fresh user (no existing config)
        garmin_repo.save_credentials(
            user_id="fresh-user-for-defaults",
            encrypted_email="email",
            encrypted_password="pass",
        )
        config = garmin_repo.update_sync_config("fresh-user-for-defaults")

        # Check defaults are set correctly for new config
        assert config.sync_frequency == "daily"
        assert config.sync_time == "06:00"
        assert config.initial_sync_days == 365
        assert config.incremental_sync_days == 7
        assert config.min_sync_interval_minutes == 60

    def test_update_sync_config_partial_update(self, garmin_repo, sample_credentials):
        """Should update only specified fields."""
        # Create initial config
        garmin_repo.update_sync_config(
            sample_credentials.user_id,
            sync_frequency="daily",
            sync_time="06:00",
        )

        # Update only frequency
        config = garmin_repo.update_sync_config(
            sample_credentials.user_id,
            sync_frequency="hourly",
        )

        assert config.sync_frequency == "hourly"
        assert config.sync_time == "06:00"  # Unchanged

    def test_update_sync_config_all_fields(self, garmin_repo, sample_credentials):
        """Should update all configurable fields."""
        config = garmin_repo.update_sync_config(
            sample_credentials.user_id,
            auto_sync_enabled=False,
            sync_frequency="weekly",
            sync_time="12:00",
            sync_activities=False,
            sync_wellness=False,
            sync_fitness_metrics=False,
            sync_sleep=False,
            initial_sync_days=90,
            incremental_sync_days=3,
            min_sync_interval_minutes=120,
        )

        assert config.auto_sync_enabled is False
        assert config.sync_frequency == "weekly"
        assert config.sync_time == "12:00"
        assert config.sync_activities is False
        assert config.sync_wellness is False
        assert config.sync_fitness_metrics is False
        assert config.sync_sleep is False
        assert config.initial_sync_days == 90
        assert config.incremental_sync_days == 3
        assert config.min_sync_interval_minutes == 120


class TestSyncHistory:
    """Tests for sync history tracking."""

    def test_start_sync(self, garmin_repo, sample_credentials):
        """Should create sync history record."""
        sync_id = garmin_repo.start_sync(
            sample_credentials.user_id,
            sync_type="manual",
            sync_from_date=date.today() - timedelta(days=7),
            sync_to_date=date.today(),
        )

        assert sync_id > 0

        history = garmin_repo.get_sync_history(sample_credentials.user_id)
        assert len(history) == 1
        assert history[0].id == sync_id
        assert history[0].sync_type == "manual"
        assert history[0].status == "running"

    def test_complete_sync_success(self, garmin_repo, sample_credentials):
        """Should complete sync with success status."""
        sync_id = garmin_repo.start_sync(
            sample_credentials.user_id,
            sync_type="scheduled",
        )

        import time
        time.sleep(0.01)  # Small delay

        result = garmin_repo.complete_sync(
            sync_id,
            status="completed",
            activities_synced=10,
            wellness_days_synced=7,
            fitness_days_synced=7,
        )

        assert result is True

        history = garmin_repo.get_sync_history(sample_credentials.user_id)
        assert history[0].status == "completed"
        assert history[0].activities_synced == 10
        assert history[0].wellness_days_synced == 7
        assert history[0].fitness_days_synced == 7
        assert history[0].duration_seconds >= 0
        assert history[0].completed_at is not None

    def test_complete_sync_failure(self, garmin_repo, sample_credentials):
        """Should complete sync with failure status."""
        sync_id = garmin_repo.start_sync(
            sample_credentials.user_id,
            sync_type="manual",
        )

        result = garmin_repo.complete_sync(
            sync_id,
            status="failed",
            error_message="Connection timeout",
            error_details='{"attempt": 3, "timeout": 30}',
        )

        assert result is True

        history = garmin_repo.get_sync_history(sample_credentials.user_id)
        assert history[0].status == "failed"
        assert history[0].error_message == "Connection timeout"
        assert history[0].error_details is not None

    def test_complete_sync_partial(self, garmin_repo, sample_credentials):
        """Should complete sync with partial status."""
        sync_id = garmin_repo.start_sync(
            sample_credentials.user_id,
            sync_type="scheduled",
        )

        result = garmin_repo.complete_sync(
            sync_id,
            status="partial",
            activities_synced=5,
            error_message="Some activities failed to sync",
        )

        assert result is True

        history = garmin_repo.get_sync_history(sample_credentials.user_id)
        assert history[0].status == "partial"
        assert history[0].activities_synced == 5

    def test_complete_sync_not_found(self, garmin_repo):
        """Should return False for non-existent sync ID."""
        result = garmin_repo.complete_sync(
            99999,
            status="completed",
        )
        assert result is False

    def test_get_sync_history_limit(self, garmin_repo, sample_credentials):
        """Should respect limit parameter."""
        # Create multiple sync records
        for _ in range(15):
            sync_id = garmin_repo.start_sync(
                sample_credentials.user_id,
                sync_type="scheduled",
            )
            garmin_repo.complete_sync(sync_id, status="completed")

        history = garmin_repo.get_sync_history(
            sample_credentials.user_id,
            limit=5,
        )

        assert len(history) == 5

    def test_get_sync_history_ordered_by_date(self, garmin_repo, sample_credentials):
        """Sync history should be ordered by started_at descending."""
        for i in range(3):
            sync_id = garmin_repo.start_sync(
                sample_credentials.user_id,
                sync_type="scheduled",
            )
            garmin_repo.complete_sync(sync_id, status="completed")

        history = garmin_repo.get_sync_history(sample_credentials.user_id)

        for i in range(len(history) - 1):
            assert history[i].started_at >= history[i + 1].started_at

    def test_get_last_successful_sync(self, garmin_repo, sample_credentials):
        """Should get most recent successful sync."""
        # Create some syncs
        sync1 = garmin_repo.start_sync(sample_credentials.user_id, sync_type="manual")
        garmin_repo.complete_sync(sync1, status="completed", activities_synced=5)

        sync2 = garmin_repo.start_sync(sample_credentials.user_id, sync_type="manual")
        garmin_repo.complete_sync(sync2, status="failed", error_message="Error")

        sync3 = garmin_repo.start_sync(sample_credentials.user_id, sync_type="manual")
        garmin_repo.complete_sync(sync3, status="completed", activities_synced=10)

        last_success = garmin_repo.get_last_successful_sync(sample_credentials.user_id)

        assert last_success is not None
        assert last_success.id == sync3
        assert last_success.activities_synced == 10

    def test_get_last_successful_sync_none(self, garmin_repo, sample_credentials):
        """Should return None when no successful sync exists."""
        sync_id = garmin_repo.start_sync(sample_credentials.user_id, sync_type="manual")
        garmin_repo.complete_sync(sync_id, status="failed", error_message="Error")

        last_success = garmin_repo.get_last_successful_sync(sample_credentials.user_id)
        assert last_success is None


class TestAutoSyncUsers:
    """Tests for auto-sync user listing."""

    def test_get_all_auto_sync_users_empty(self, garmin_repo):
        """Should return empty list when no users qualify."""
        users = garmin_repo.get_all_auto_sync_users()
        assert users == []

    def test_get_all_auto_sync_users(self, garmin_repo):
        """Should return users with valid credentials and auto-sync enabled."""
        # User 1: Valid credentials, auto-sync enabled
        garmin_repo.save_credentials(
            user_id="user-1",
            encrypted_email="email1",
            encrypted_password="pass1",
        )
        garmin_repo.update_sync_config("user-1", auto_sync_enabled=True)

        # User 2: Valid credentials, auto-sync disabled
        garmin_repo.save_credentials(
            user_id="user-2",
            encrypted_email="email2",
            encrypted_password="pass2",
        )
        garmin_repo.update_sync_config("user-2", auto_sync_enabled=False)

        # User 3: Invalid credentials, auto-sync enabled
        garmin_repo.save_credentials(
            user_id="user-3",
            encrypted_email="email3",
            encrypted_password="pass3",
        )
        garmin_repo.update_validation_status("user-3", is_valid=False)
        garmin_repo.update_sync_config("user-3", auto_sync_enabled=True)

        # User 4: Valid credentials, auto-sync enabled
        garmin_repo.save_credentials(
            user_id="user-4",
            encrypted_email="email4",
            encrypted_password="pass4",
        )
        garmin_repo.update_sync_config("user-4", auto_sync_enabled=True)

        users = garmin_repo.get_all_auto_sync_users()

        assert len(users) == 2
        assert "user-1" in users
        assert "user-4" in users
        assert "user-2" not in users  # Auto-sync disabled
        assert "user-3" not in users  # Invalid credentials


class TestDataclasses:
    """Tests for Garmin-related dataclasses."""

    def test_garmin_credentials_defaults(self):
        """GarminCredentials should have sensible defaults."""
        creds = GarminCredentials(
            user_id="test",
            encrypted_email="email",
            encrypted_password="pass",
        )

        assert creds.encryption_key_id == "v1"
        assert creds.oauth1_token is None
        assert creds.oauth1_token_secret is None
        assert creds.session_data is None
        assert creds.garmin_user_id is None
        assert creds.garmin_display_name is None
        assert creds.is_valid is True
        assert creds.validation_error is None

    def test_garmin_sync_config_defaults(self):
        """GarminSyncConfig should have sensible defaults."""
        config = GarminSyncConfig(user_id="test")

        assert config.auto_sync_enabled is True
        assert config.sync_frequency == "daily"
        assert config.sync_time == "06:00"
        assert config.sync_activities is True
        assert config.sync_wellness is True
        assert config.sync_fitness_metrics is True
        assert config.sync_sleep is True
        assert config.initial_sync_days == 365
        assert config.incremental_sync_days == 7
        assert config.min_sync_interval_minutes == 60

    def test_garmin_sync_history_defaults(self):
        """GarminSyncHistory should have sensible defaults."""
        now = datetime.now()
        history = GarminSyncHistory(
            id=1,
            user_id="test",
            sync_type="manual",
            started_at=now,
        )

        assert history.completed_at is None
        assert history.duration_seconds is None
        assert history.status == "running"
        assert history.activities_synced == 0
        assert history.wellness_days_synced == 0
        assert history.fitness_days_synced == 0
        assert history.error_message is None
        assert history.error_details is None
        assert history.retry_count == 0


class TestSingletonPattern:
    """Tests for singleton repository pattern."""

    def test_get_garmin_credentials_repository_returns_singleton(self, monkeypatch):
        """get_garmin_credentials_repository should return same instance."""
        from training_analyzer.db.repositories import garmin_credentials_repository
        monkeypatch.setattr(garmin_credentials_repository, "_garmin_credentials_repository", None)

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            monkeypatch.setenv("TRAINING_DB_PATH", temp_path)

            repo1 = get_garmin_credentials_repository()
            repo2 = get_garmin_credentials_repository()

            assert repo1 is repo2
        finally:
            monkeypatch.setattr(garmin_credentials_repository, "_garmin_credentials_repository", None)
            try:
                os.unlink(temp_path)
            except OSError:
                pass
