"""
SQLite Connection Pool for improved database performance.

This module implements a connection pool for SQLite databases with:
- Configurable pool size
- WAL mode for concurrent reads
- NORMAL synchronous mode for better write performance
- 64MB cache size
- Thread-safe connection management
- Context manager for automatic connection recycling

Usage:
    pool = SQLiteConnectionPool("path/to/db.sqlite", pool_size=5)

    with pool.get_connection() as conn:
        conn.execute("SELECT * FROM table")
        # Connection is automatically returned to pool after the block

    # Clean shutdown
    pool.close()
"""

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from queue import Queue, Empty
from typing import Optional, Union


class SQLiteConnectionPool:
    """
    Thread-safe SQLite connection pool with performance optimizations.

    Attributes:
        db_path: Path to the SQLite database file
        pool_size: Maximum number of connections in the pool
        timeout: Timeout in seconds for acquiring a connection
    """

    def __init__(
        self,
        db_path: Union[str, Path],
        pool_size: int = 5,
        timeout: float = 30.0
    ):
        """
        Initialize the connection pool.

        Args:
            db_path: Path to the SQLite database file
            pool_size: Maximum number of connections to maintain (default: 5)
            timeout: Timeout in seconds for acquiring a connection (default: 30)
        """
        self.db_path = Path(db_path)
        self.pool_size = pool_size
        self.timeout = timeout
        self._pool: Queue[sqlite3.Connection] = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._closed = False
        self._connections_created = 0

        # Pre-populate the pool with connections
        self._initialize_pool()

    def _initialize_pool(self) -> None:
        """Pre-populate the connection pool."""
        for _ in range(self.pool_size):
            conn = self._create_connection()
            self._pool.put(conn)
            self._connections_created += 1

    def _create_connection(self) -> sqlite3.Connection:
        """
        Create a new database connection with performance optimizations.

        Performance settings applied:
        - WAL journal mode: Allows concurrent reads during writes
        - NORMAL synchronous: Faster writes with acceptable durability
        - 64MB cache: Larger cache for better read performance
        - MEMORY temp store: Use RAM for temporary tables
        - Row factory: sqlite3.Row for dict-like access

        Returns:
            Configured sqlite3.Connection
        """
        conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,  # Allow connection sharing between threads
            isolation_level=None  # Autocommit mode, we manage transactions manually
        )
        conn.row_factory = sqlite3.Row

        # Apply performance optimizations
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-64000")  # 64MB cache (negative = KB)
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O
        conn.execute("PRAGMA busy_timeout=5000")  # 5 second busy timeout

        return conn

    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool using a context manager.

        Usage:
            with pool.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM table")
                results = cursor.fetchall()

        The connection is automatically returned to the pool after the
        context manager exits, whether normally or via an exception.

        If an exception occurs, the transaction is rolled back.
        Otherwise, changes are committed.

        Yields:
            sqlite3.Connection from the pool

        Raises:
            RuntimeError: If the pool is closed
            queue.Empty: If timeout expires waiting for a connection
        """
        if self._closed:
            raise RuntimeError("Connection pool is closed")

        conn = None
        try:
            # Get a connection from the pool
            conn = self._pool.get(timeout=self.timeout)

            # Start a transaction
            conn.execute("BEGIN")

            yield conn

            # Commit on success
            conn.execute("COMMIT")

        except Exception:
            # Rollback on error
            if conn:
                try:
                    conn.execute("ROLLBACK")
                except sqlite3.Error:
                    # Connection might be broken, will be replaced
                    pass
            raise

        finally:
            # Return connection to pool
            if conn:
                self._return_connection(conn)

    def _return_connection(self, conn: sqlite3.Connection) -> None:
        """
        Return a connection to the pool.

        If the connection appears broken, create a new one instead.

        Args:
            conn: Connection to return
        """
        try:
            # Test if connection is still valid
            conn.execute("SELECT 1")
            self._pool.put(conn)
        except sqlite3.Error:
            # Connection is broken, create a new one
            try:
                conn.close()
            except sqlite3.Error:
                pass
            new_conn = self._create_connection()
            self._pool.put(new_conn)

    def close(self) -> None:
        """
        Close all connections in the pool.

        This should be called during application shutdown.
        """
        with self._lock:
            self._closed = True

            # Close all connections in the pool
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    conn.close()
                except Empty:
                    break
                except sqlite3.Error:
                    pass  # Ignore errors during cleanup

    @property
    def available_connections(self) -> int:
        """Return the number of connections currently available in the pool."""
        return self._pool.qsize()

    @property
    def is_closed(self) -> bool:
        """Return True if the pool has been closed."""
        return self._closed

    def execute_query(self, query: str, params: tuple = ()) -> list:
        """
        Execute a query and return all results.

        Convenience method for simple queries.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            List of rows as sqlite3.Row objects
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """
        Execute an update/insert/delete and return affected row count.

        Convenience method for simple updates.

        Args:
            query: SQL statement to execute
            params: Query parameters

        Returns:
            Number of rows affected
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount

    def __enter__(self):
        """Support using the pool as a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the pool when exiting context."""
        self.close()
        return False

    def __del__(self):
        """Clean up connections on garbage collection."""
        if not self._closed:
            self.close()


# Singleton instance for the training database
_default_pool: Optional[SQLiteConnectionPool] = None
_pool_lock = threading.Lock()


def get_connection_pool(
    db_path: Optional[Union[str, Path]] = None,
    pool_size: int = 5
) -> SQLiteConnectionPool:
    """
    Get or create the default connection pool.

    This function provides a singleton pattern for the connection pool,
    ensuring only one pool is created per database path.

    Args:
        db_path: Path to database. If None, uses default training.db location
        pool_size: Pool size (only used when creating a new pool)

    Returns:
        SQLiteConnectionPool instance
    """
    global _default_pool

    with _pool_lock:
        if _default_pool is None or _default_pool.is_closed:
            if db_path is None:
                # Use default path from environment or default location
                import os
                env_path = os.environ.get("TRAINING_DB_PATH")
                if env_path:
                    db_path = Path(env_path)
                else:
                    # Default to training-analyzer/training.db
                    db_path = Path(__file__).parent.parent.parent / "training.db"

            _default_pool = SQLiteConnectionPool(db_path, pool_size=pool_size)

        return _default_pool


def close_default_pool() -> None:
    """Close the default connection pool."""
    global _default_pool

    with _pool_lock:
        if _default_pool is not None:
            _default_pool.close()
            _default_pool = None
