"""SQLite-backed repository for user management.

Provides CRUD operations for users in the multi-user platform,
supporting user authentication, profile management, and user data isolation.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class User:
    """User entity representing a platform user."""

    id: str
    email: str
    email_verified: bool = False
    password_hash: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: str = "UTC"
    is_active: bool = True
    is_admin: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


class UserRepository:
    """
    SQLite-backed repository for User entities.

    Provides user management operations including creation, retrieval,
    update, deletion, and login tracking for the multi-user platform.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the user repository.

        Args:
            db_path: Path to SQLite database file. If None, uses the default
                    training.db in the training-analyzer directory.
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            import os
            env_path = os.environ.get("TRAINING_DB_PATH")
            if env_path:
                self.db_path = Path(env_path)
            else:
                self.db_path = Path(__file__).parent.parent.parent.parent.parent / "training.db"

        self._ensure_table_exists()

    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_table_exists(self):
        """Ensure the users table exists."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    email_verified INTEGER DEFAULT 0,
                    password_hash TEXT,
                    display_name TEXT,
                    avatar_url TEXT,
                    timezone TEXT DEFAULT 'UTC',
                    is_active INTEGER DEFAULT 1,
                    is_admin INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_login_at TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
            """)

    def _row_to_user(self, row: sqlite3.Row) -> User:
        """Convert a database row to a User entity."""
        created_at = row["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        updated_at = row["updated_at"]
        if isinstance(updated_at, str) and updated_at:
            updated_at = datetime.fromisoformat(updated_at)

        last_login_at = row["last_login_at"]
        if isinstance(last_login_at, str) and last_login_at:
            last_login_at = datetime.fromisoformat(last_login_at)

        return User(
            id=row["id"],
            email=row["email"],
            email_verified=bool(row["email_verified"]),
            password_hash=row["password_hash"],
            display_name=row["display_name"],
            avatar_url=row["avatar_url"],
            timezone=row["timezone"] or "UTC",
            is_active=bool(row["is_active"]),
            is_admin=bool(row["is_admin"]),
            created_at=created_at,
            updated_at=updated_at,
            last_login_at=last_login_at,
        )

    def create_user(
        self,
        user_id: str,
        email: str,
        password_hash: Optional[str] = None,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        timezone: str = "UTC",
        email_verified: bool = False,
    ) -> User:
        """
        Create a new user in the database.

        Args:
            user_id: Unique identifier for the user (UUID)
            email: User's email address (must be unique)
            password_hash: Bcrypt hash of password (None for OAuth users)
            display_name: User's display name
            avatar_url: URL to user's avatar image
            timezone: User's timezone (default: UTC)
            email_verified: Whether email has been verified

        Returns:
            The created User entity

        Raises:
            sqlite3.IntegrityError: If email already exists
        """
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO users
                (id, email, password_hash, display_name, avatar_url,
                 timezone, email_verified, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                email,
                password_hash,
                display_name,
                avatar_url,
                timezone,
                1 if email_verified else 0,
                now,
                now,
            ))

        return User(
            id=user_id,
            email=email,
            email_verified=email_verified,
            password_hash=password_hash,
            display_name=display_name,
            avatar_url=avatar_url,
            timezone=timezone,
            is_active=True,
            is_admin=False,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
            last_login_at=None,
        )

    def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Retrieve a user by their unique ID.

        Args:
            user_id: The user's unique identifier

        Returns:
            The User entity if found, None otherwise
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()

            if row:
                return self._row_to_user(row)
            return None

    def get_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve a user by their email address.

        Args:
            email: The user's email address

        Returns:
            The User entity if found, None otherwise
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,)
            ).fetchone()

            if row:
                return self._row_to_user(row)
            return None

    def update(
        self,
        user_id: str,
        email: Optional[str] = None,
        password_hash: Optional[str] = None,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        timezone: Optional[str] = None,
        email_verified: Optional[bool] = None,
        is_active: Optional[bool] = None,
        is_admin: Optional[bool] = None,
    ) -> Optional[User]:
        """
        Update an existing user's information.

        Only provided fields will be updated. None values are ignored.

        Args:
            user_id: The user's unique identifier
            email: New email address
            password_hash: New password hash
            display_name: New display name
            avatar_url: New avatar URL
            timezone: New timezone
            email_verified: New email verification status
            is_active: New active status
            is_admin: New admin status

        Returns:
            The updated User entity if found, None otherwise
        """
        updates = []
        params = []

        if email is not None:
            updates.append("email = ?")
            params.append(email)
        if password_hash is not None:
            updates.append("password_hash = ?")
            params.append(password_hash)
        if display_name is not None:
            updates.append("display_name = ?")
            params.append(display_name)
        if avatar_url is not None:
            updates.append("avatar_url = ?")
            params.append(avatar_url)
        if timezone is not None:
            updates.append("timezone = ?")
            params.append(timezone)
        if email_verified is not None:
            updates.append("email_verified = ?")
            params.append(1 if email_verified else 0)
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if is_active else 0)
        if is_admin is not None:
            updates.append("is_admin = ?")
            params.append(1 if is_admin else 0)

        if not updates:
            return self.get_by_id(user_id)

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(user_id)

        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            if cursor.rowcount == 0:
                return None

        return self.get_by_id(user_id)

    def delete(self, user_id: str) -> bool:
        """
        Delete a user from the database.

        Args:
            user_id: The user's unique identifier

        Returns:
            True if the user was deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM users WHERE id = ?",
                (user_id,)
            )
            return cursor.rowcount > 0

    def update_last_login(self, user_id: str) -> bool:
        """
        Update the user's last login timestamp to now.

        Args:
            user_id: The user's unique identifier

        Returns:
            True if the update was successful, False if user not found
        """
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?",
                (now, now, user_id)
            )
            return cursor.rowcount > 0

    def exists(self, user_id: str) -> bool:
        """
        Check if a user exists by their ID.

        Args:
            user_id: The user's unique identifier

        Returns:
            True if the user exists, False otherwise
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()
            return row is not None

    def email_exists(self, email: str) -> bool:
        """
        Check if an email address is already registered.

        Args:
            email: The email address to check

        Returns:
            True if the email exists, False otherwise
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM users WHERE email = ?",
                (email,)
            ).fetchone()
            return row is not None

    def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        active_only: bool = True,
    ) -> List[User]:
        """
        Retrieve all users with pagination.

        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            active_only: If True, only return active users

        Returns:
            List of User entities
        """
        query = "SELECT * FROM users"
        params = []

        if active_only:
            query += " WHERE is_active = 1"

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_user(row) for row in rows]

    def count(self, active_only: bool = True) -> int:
        """
        Count the total number of users.

        Args:
            active_only: If True, only count active users

        Returns:
            The number of users
        """
        query = "SELECT COUNT(*) as cnt FROM users"

        if active_only:
            query += " WHERE is_active = 1"

        with self._get_connection() as conn:
            row = conn.execute(query).fetchone()
            return row["cnt"]


# Singleton instance for dependency injection
_user_repository: Optional[UserRepository] = None


def get_user_repository() -> UserRepository:
    """Get or create the singleton UserRepository instance."""
    global _user_repository
    if _user_repository is None:
        _user_repository = UserRepository()
    return _user_repository
