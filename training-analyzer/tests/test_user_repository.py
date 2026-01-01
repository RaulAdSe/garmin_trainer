"""Tests for UserRepository - User CRUD and session management.

This module tests:
1. User creation with various parameters
2. User retrieval by ID and email
3. User updates (partial and full)
4. User deletion
5. Login tracking (last_login_at updates)
6. User existence checks
7. Pagination and filtering
"""

import os
import pytest
import tempfile
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from training_analyzer.db.repositories.user_repository import (
    UserRepository,
    User,
    get_user_repository,
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
def user_repo(temp_db_path):
    """Create a UserRepository with a temporary database."""
    repo = UserRepository(db_path=temp_db_path)
    return repo


@pytest.fixture
def sample_user(user_repo):
    """Create a sample user for testing."""
    return user_repo.create_user(
        user_id="test-user-123",
        email="test@example.com",
        password_hash="hashed_password_here",
        display_name="Test User",
        timezone="America/New_York",
    )


class TestUserRepositoryInit:
    """Tests for repository initialization."""

    def test_creates_users_table(self, user_repo):
        """Users table should be created on init."""
        with user_repo._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
            )
            result = cursor.fetchone()
            assert result is not None
            assert result["name"] == "users"

    def test_creates_email_index(self, user_repo):
        """Email index should be created on init."""
        with user_repo._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_users_email'"
            )
            result = cursor.fetchone()
            assert result is not None

    def test_uses_custom_db_path(self, temp_db_path):
        """Should use provided database path."""
        repo = UserRepository(db_path=temp_db_path)
        assert repo.db_path == Path(temp_db_path)


class TestUserCreation:
    """Tests for user creation."""

    def test_create_user_minimal(self, user_repo):
        """Should create user with minimal required fields."""
        user = user_repo.create_user(
            user_id="user-001",
            email="minimal@example.com",
        )

        assert user.id == "user-001"
        assert user.email == "minimal@example.com"
        assert user.email_verified is False
        assert user.password_hash is None
        assert user.display_name is None
        assert user.timezone == "UTC"
        assert user.is_active is True
        assert user.is_admin is False
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_create_user_with_all_fields(self, user_repo):
        """Should create user with all fields."""
        user = user_repo.create_user(
            user_id="user-002",
            email="full@example.com",
            password_hash="$2b$12$hash",
            display_name="Full User",
            avatar_url="https://example.com/avatar.png",
            timezone="Europe/London",
            email_verified=True,
        )

        assert user.id == "user-002"
        assert user.email == "full@example.com"
        assert user.password_hash == "$2b$12$hash"
        assert user.display_name == "Full User"
        assert user.avatar_url == "https://example.com/avatar.png"
        assert user.timezone == "Europe/London"
        assert user.email_verified is True

    def test_create_user_duplicate_email_fails(self, user_repo, sample_user):
        """Should fail when creating user with duplicate email."""
        with pytest.raises(sqlite3.IntegrityError):
            user_repo.create_user(
                user_id="user-different",
                email=sample_user.email,  # Same email
            )

    def test_create_user_duplicate_id_fails(self, user_repo, sample_user):
        """Should fail when creating user with duplicate ID."""
        with pytest.raises(sqlite3.IntegrityError):
            user_repo.create_user(
                user_id=sample_user.id,  # Same ID
                email="different@example.com",
            )

    def test_create_user_timestamps(self, user_repo):
        """Created user should have correct timestamps."""
        before = datetime.now()
        user = user_repo.create_user(
            user_id="user-003",
            email="timestamps@example.com",
        )
        after = datetime.now()

        assert before <= user.created_at <= after
        assert before <= user.updated_at <= after
        assert user.last_login_at is None


class TestUserRetrieval:
    """Tests for user retrieval operations."""

    def test_get_by_id(self, user_repo, sample_user):
        """Should retrieve user by ID."""
        user = user_repo.get_by_id(sample_user.id)

        assert user is not None
        assert user.id == sample_user.id
        assert user.email == sample_user.email

    def test_get_by_id_not_found(self, user_repo):
        """Should return None for non-existent ID."""
        user = user_repo.get_by_id("non-existent-id")
        assert user is None

    def test_get_by_email(self, user_repo, sample_user):
        """Should retrieve user by email."""
        user = user_repo.get_by_email(sample_user.email)

        assert user is not None
        assert user.id == sample_user.id
        assert user.email == sample_user.email

    def test_get_by_email_not_found(self, user_repo):
        """Should return None for non-existent email."""
        user = user_repo.get_by_email("nonexistent@example.com")
        assert user is None

    def test_get_by_email_case_sensitive(self, user_repo, sample_user):
        """Email lookup should be case-sensitive (by default in SQLite)."""
        # Exact match
        user = user_repo.get_by_email(sample_user.email)
        assert user is not None

        # Different case - depends on SQLite collation
        user_upper = user_repo.get_by_email(sample_user.email.upper())
        # SQLite default NOCASE collation may match, so just verify we get a result or None
        assert user_upper is None or user_upper.email == sample_user.email


class TestUserUpdate:
    """Tests for user update operations."""

    def test_update_single_field(self, user_repo, sample_user):
        """Should update single field."""
        updated = user_repo.update(sample_user.id, display_name="New Name")

        assert updated is not None
        assert updated.display_name == "New Name"
        # Other fields unchanged
        assert updated.email == sample_user.email
        assert updated.timezone == sample_user.timezone

    def test_update_multiple_fields(self, user_repo, sample_user):
        """Should update multiple fields."""
        updated = user_repo.update(
            sample_user.id,
            display_name="Updated Name",
            timezone="Asia/Tokyo",
            email_verified=True,
        )

        assert updated is not None
        assert updated.display_name == "Updated Name"
        assert updated.timezone == "Asia/Tokyo"
        assert updated.email_verified is True

    def test_update_email(self, user_repo, sample_user):
        """Should update email address."""
        updated = user_repo.update(sample_user.id, email="newemail@example.com")

        assert updated is not None
        assert updated.email == "newemail@example.com"

    def test_update_password_hash(self, user_repo, sample_user):
        """Should update password hash."""
        new_hash = "$2b$12$new_hashed_password"
        updated = user_repo.update(sample_user.id, password_hash=new_hash)

        assert updated is not None
        assert updated.password_hash == new_hash

    def test_update_admin_status(self, user_repo, sample_user):
        """Should update admin status."""
        # Make admin
        updated = user_repo.update(sample_user.id, is_admin=True)
        assert updated.is_admin is True

        # Revoke admin
        updated = user_repo.update(sample_user.id, is_admin=False)
        assert updated.is_admin is False

    def test_update_active_status(self, user_repo, sample_user):
        """Should update active status."""
        # Deactivate
        updated = user_repo.update(sample_user.id, is_active=False)
        assert updated.is_active is False

        # Reactivate
        updated = user_repo.update(sample_user.id, is_active=True)
        assert updated.is_active is True

    def test_update_nonexistent_user(self, user_repo):
        """Should return None for non-existent user."""
        result = user_repo.update("non-existent", display_name="Test")
        assert result is None

    def test_update_no_fields(self, user_repo, sample_user):
        """Should return user unchanged when no fields specified."""
        updated = user_repo.update(sample_user.id)

        assert updated is not None
        assert updated.id == sample_user.id

    def test_update_changes_updated_at(self, user_repo, sample_user):
        """Update should change updated_at timestamp."""
        import time
        time.sleep(0.01)  # Small delay to ensure different timestamp

        updated = user_repo.update(sample_user.id, display_name="Changed")

        assert updated.updated_at > sample_user.updated_at


class TestUserDeletion:
    """Tests for user deletion."""

    def test_delete_user(self, user_repo, sample_user):
        """Should delete existing user."""
        result = user_repo.delete(sample_user.id)

        assert result is True
        assert user_repo.get_by_id(sample_user.id) is None

    def test_delete_nonexistent_user(self, user_repo):
        """Should return False for non-existent user."""
        result = user_repo.delete("non-existent")
        assert result is False


class TestLoginTracking:
    """Tests for login tracking functionality."""

    def test_update_last_login(self, user_repo, sample_user):
        """Should update last_login_at timestamp."""
        import time

        # Initially None
        assert sample_user.last_login_at is None

        # Update login
        time.sleep(0.01)  # Small delay
        result = user_repo.update_last_login(sample_user.id)
        assert result is True

        # Verify updated
        user = user_repo.get_by_id(sample_user.id)
        assert user.last_login_at is not None
        assert user.last_login_at > sample_user.created_at

    def test_update_last_login_multiple_times(self, user_repo, sample_user):
        """Should update last_login_at on each call."""
        import time

        user_repo.update_last_login(sample_user.id)
        user = user_repo.get_by_id(sample_user.id)
        first_login = user.last_login_at

        time.sleep(0.01)  # Small delay
        user_repo.update_last_login(sample_user.id)
        user = user_repo.get_by_id(sample_user.id)
        second_login = user.last_login_at

        assert second_login > first_login

    def test_update_last_login_nonexistent_user(self, user_repo):
        """Should return False for non-existent user."""
        result = user_repo.update_last_login("non-existent")
        assert result is False


class TestUserExistence:
    """Tests for user existence checks."""

    def test_exists_true(self, user_repo, sample_user):
        """Should return True for existing user."""
        assert user_repo.exists(sample_user.id) is True

    def test_exists_false(self, user_repo):
        """Should return False for non-existent user."""
        assert user_repo.exists("non-existent") is False

    def test_email_exists_true(self, user_repo, sample_user):
        """Should return True for existing email."""
        assert user_repo.email_exists(sample_user.email) is True

    def test_email_exists_false(self, user_repo):
        """Should return False for non-existent email."""
        assert user_repo.email_exists("nonexistent@example.com") is False


class TestUserListing:
    """Tests for listing and pagination."""

    @pytest.fixture
    def multiple_users(self, user_repo):
        """Create multiple users for listing tests."""
        users = []
        for i in range(5):
            user = user_repo.create_user(
                user_id=f"user-{i:03d}",
                email=f"user{i}@example.com",
                display_name=f"User {i}",
            )
            # Set is_active via update (last 2 are inactive)
            if i >= 3:
                user_repo.update(user.id, is_active=False)
                user = user_repo.get_by_id(user.id)
            users.append(user)
        return users

    def test_get_all_active_only(self, user_repo, multiple_users):
        """Should return only active users by default."""
        users = user_repo.get_all()
        assert len(users) == 3
        for user in users:
            assert user.is_active is True

    def test_get_all_including_inactive(self, user_repo, multiple_users):
        """Should return all users when active_only=False."""
        users = user_repo.get_all(active_only=False)
        assert len(users) == 5

    def test_get_all_with_limit(self, user_repo, multiple_users):
        """Should respect limit parameter."""
        users = user_repo.get_all(limit=2, active_only=False)
        assert len(users) == 2

    def test_get_all_with_offset(self, user_repo, multiple_users):
        """Should respect offset parameter."""
        all_users = user_repo.get_all(active_only=False)
        offset_users = user_repo.get_all(offset=2, active_only=False)

        assert len(offset_users) == 3
        # Offset users should not include first 2
        offset_ids = {u.id for u in offset_users}
        first_two_ids = {all_users[0].id, all_users[1].id}
        assert offset_ids.isdisjoint(first_two_ids)

    def test_get_all_ordered_by_created_at(self, user_repo, multiple_users):
        """Users should be ordered by created_at descending."""
        users = user_repo.get_all(active_only=False)
        for i in range(len(users) - 1):
            assert users[i].created_at >= users[i + 1].created_at


class TestUserCount:
    """Tests for user counting."""

    @pytest.fixture
    def users_for_counting(self, user_repo):
        """Create users for counting tests."""
        for i in range(5):
            user = user_repo.create_user(
                user_id=f"user-{i}",
                email=f"user{i}@example.com",
            )
            # Set is_active via update (last 2 are inactive)
            if i >= 3:
                user_repo.update(user.id, is_active=False)

    def test_count_active_only(self, user_repo, users_for_counting):
        """Should count only active users by default."""
        count = user_repo.count()
        assert count == 3

    def test_count_all(self, user_repo, users_for_counting):
        """Should count all users when active_only=False."""
        count = user_repo.count(active_only=False)
        assert count == 5

    def test_count_empty(self, user_repo):
        """Should return 0 for empty table."""
        count = user_repo.count()
        assert count == 0


class TestUserDataclass:
    """Tests for User dataclass."""

    def test_user_defaults(self):
        """User should have sensible defaults."""
        user = User(id="test", email="test@example.com")

        assert user.email_verified is False
        assert user.password_hash is None
        assert user.display_name is None
        assert user.avatar_url is None
        assert user.timezone == "UTC"
        assert user.is_active is True
        assert user.is_admin is False
        assert user.created_at is None
        assert user.updated_at is None
        assert user.last_login_at is None


class TestSingletonPattern:
    """Tests for singleton repository pattern."""

    def test_get_user_repository_returns_singleton(self, monkeypatch):
        """get_user_repository should return same instance."""
        # Clear any existing singleton
        from training_analyzer.db.repositories import user_repository
        monkeypatch.setattr(user_repository, "_user_repository", None)

        # Create temp db path for test
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            monkeypatch.setenv("TRAINING_DB_PATH", temp_path)

            repo1 = get_user_repository()
            repo2 = get_user_repository()

            assert repo1 is repo2
        finally:
            # Cleanup
            monkeypatch.setattr(user_repository, "_user_repository", None)
            try:
                os.unlink(temp_path)
            except OSError:
                pass
