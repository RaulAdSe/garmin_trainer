"""SQLite-backed repository for LLM analysis result caching.

Caches LLM analysis results to save API costs by not re-analyzing
the same workout or data. Supports:
- TTL-based cache expiration
- Cache hit tracking for analytics
- Multiple analysis types
"""

import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from dataclasses import dataclass

from .base import CachingRepository


@dataclass
class AnalysisCacheEntry:
    """Represents a cached analysis result."""
    cache_key: str
    analysis_type: str
    input_hash: str
    result: Dict[str, Any]
    model_name: Optional[str] = None
    tokens_used: Optional[int] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    hit_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cache_key": self.cache_key,
            "analysis_type": self.analysis_type,
            "input_hash": self.input_hash,
            "result": self.result,
            "model_name": self.model_name,
            "tokens_used": self.tokens_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "hit_count": self.hit_count,
        }


class AnalysisCacheRepository(CachingRepository[AnalysisCacheEntry]):
    """
    SQLite-backed repository for caching LLM analysis results.

    Provides persistent caching for analysis results to reduce API costs
    and improve response times for repeated queries.
    """

    # Default TTL for cache entries (24 hours)
    DEFAULT_TTL_SECONDS = 86400

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the analysis cache repository.

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
                self.db_path = Path(__file__).parent.parent.parent.parent / "training.db"

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
        """Ensure the analysis_cache table exists."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_cache (
                    cache_key TEXT PRIMARY KEY,
                    analysis_type TEXT NOT NULL,
                    input_hash TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    model_name TEXT,
                    tokens_used INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expires_at TEXT,
                    hit_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_analysis_cache_type
                ON analysis_cache(analysis_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_analysis_cache_expires
                ON analysis_cache(expires_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_analysis_cache_input_hash
                ON analysis_cache(input_hash)
            """)

    @staticmethod
    def generate_cache_key(analysis_type: str, input_data: Any) -> str:
        """
        Generate a cache key from analysis type and input data.

        Args:
            analysis_type: Type of analysis (e.g., 'workout', 'weekly')
            input_data: Input data to hash

        Returns:
            A unique cache key string
        """
        # Serialize input data to JSON for consistent hashing
        if isinstance(input_data, dict):
            input_str = json.dumps(input_data, sort_keys=True)
        elif isinstance(input_data, str):
            input_str = input_data
        else:
            input_str = str(input_data)

        # Create hash
        input_hash = hashlib.sha256(input_str.encode()).hexdigest()[:16]
        return f"{analysis_type}:{input_hash}"

    @staticmethod
    def generate_input_hash(input_data: Any) -> str:
        """
        Generate a hash of the input data for validation.

        Args:
            input_data: Input data to hash

        Returns:
            A hash string
        """
        if isinstance(input_data, dict):
            input_str = json.dumps(input_data, sort_keys=True)
        elif isinstance(input_data, str):
            input_str = input_data
        else:
            input_str = str(input_data)

        return hashlib.sha256(input_str.encode()).hexdigest()

    def _row_to_entry(self, row: sqlite3.Row) -> AnalysisCacheEntry:
        """Convert a database row to an AnalysisCacheEntry."""
        created_at = row["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        expires_at = row["expires_at"]
        if expires_at and isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)

        return AnalysisCacheEntry(
            cache_key=row["cache_key"],
            analysis_type=row["analysis_type"],
            input_hash=row["input_hash"],
            result=json.loads(row["result_json"]),
            model_name=row["model_name"],
            tokens_used=row["tokens_used"],
            created_at=created_at,
            expires_at=expires_at,
            hit_count=row["hit_count"],
        )

    def save(self, entity: AnalysisCacheEntry) -> AnalysisCacheEntry:
        """
        Save a cache entry to the database.

        Args:
            entity: The cache entry to save

        Returns:
            The saved cache entry
        """
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO analysis_cache
                (cache_key, analysis_type, input_hash, result_json,
                 model_name, tokens_used, created_at, expires_at, hit_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entity.cache_key,
                entity.analysis_type,
                entity.input_hash,
                json.dumps(entity.result),
                entity.model_name,
                entity.tokens_used,
                entity.created_at.isoformat() if entity.created_at else datetime.now().isoformat(),
                entity.expires_at.isoformat() if entity.expires_at else None,
                entity.hit_count,
            ))

        return entity

    def get(self, entity_id: str) -> Optional[AnalysisCacheEntry]:
        """
        Retrieve a cache entry by its key.

        Args:
            entity_id: The cache key

        Returns:
            The cache entry if found and not expired, None otherwise
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM analysis_cache WHERE cache_key = ?",
                (entity_id,)
            ).fetchone()

            if row:
                entry = self._row_to_entry(row)

                # Check expiration
                if entry.expires_at and entry.expires_at < datetime.now():
                    # Entry expired, delete it
                    self.delete(entity_id)
                    return None

                return entry
            return None

    def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        **filters
    ) -> List[AnalysisCacheEntry]:
        """
        Retrieve all cache entries matching the given filters.

        Args:
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            **filters: Additional filter criteria:
                - analysis_type: Filter by analysis type
                - include_expired: If True, include expired entries

        Returns:
            List of matching cache entries
        """
        query = "SELECT * FROM analysis_cache WHERE 1=1"
        params = []

        if "analysis_type" in filters:
            query += " AND analysis_type = ?"
            params.append(filters["analysis_type"])

        if not filters.get("include_expired", False):
            query += " AND (expires_at IS NULL OR expires_at > ?)"
            params.append(datetime.now().isoformat())

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_entry(row) for row in rows]

    def delete(self, entity_id: str) -> bool:
        """
        Delete a cache entry by its key.

        Args:
            entity_id: The cache key to delete

        Returns:
            True if the entry was deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM analysis_cache WHERE cache_key = ?",
                (entity_id,)
            )
            return cursor.rowcount > 0

    def exists(self, entity_id: str) -> bool:
        """
        Check if a cache entry exists and is not expired.

        Args:
            entity_id: The cache key to check

        Returns:
            True if the entry exists and is valid, False otherwise
        """
        entry = self.get(entity_id)
        return entry is not None

    def count(self, **filters) -> int:
        """
        Count cache entries matching the given filters.

        Args:
            **filters: Filter criteria (same as get_all)

        Returns:
            Number of matching entries
        """
        query = "SELECT COUNT(*) as cnt FROM analysis_cache WHERE 1=1"
        params = []

        if "analysis_type" in filters:
            query += " AND analysis_type = ?"
            params.append(filters["analysis_type"])

        if not filters.get("include_expired", False):
            query += " AND (expires_at IS NULL OR expires_at > ?)"
            params.append(datetime.now().isoformat())

        with self._get_connection() as conn:
            row = conn.execute(query, params).fetchone()
            return row["cnt"]

    # CachingRepository methods

    def get_cached(self, cache_key: str) -> Optional[AnalysisCacheEntry]:
        """
        Retrieve a cache entry and increment hit count.

        Args:
            cache_key: The cache key to look up

        Returns:
            The cached entry if found and not expired, None otherwise
        """
        entry = self.get(cache_key)

        if entry:
            # Increment hit count
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE analysis_cache SET hit_count = hit_count + 1 WHERE cache_key = ?",
                    (cache_key,)
                )
            entry.hit_count += 1

        return entry

    def set_cached(
        self,
        cache_key: str,
        entity: AnalysisCacheEntry,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Store a cache entry.

        Args:
            cache_key: The cache key to store under
            entity: The cache entry to store
            ttl_seconds: Time-to-live in seconds (None for default)
        """
        if ttl_seconds is None:
            ttl_seconds = self.DEFAULT_TTL_SECONDS

        entity.cache_key = cache_key
        entity.created_at = datetime.now()
        entity.expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

        self.save(entity)

    def invalidate_cache(self, cache_key: str) -> bool:
        """
        Invalidate a cache entry.

        Args:
            cache_key: The cache key to invalidate

        Returns:
            True if the entry was invalidated, False if not found
        """
        return self.delete(cache_key)

    def clear_cache(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM analysis_cache")
            return cursor.rowcount

    # Convenience methods

    def cache_analysis(
        self,
        analysis_type: str,
        input_data: Any,
        result: Dict[str, Any],
        model_name: Optional[str] = None,
        tokens_used: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
    ) -> AnalysisCacheEntry:
        """
        Cache an analysis result.

        Args:
            analysis_type: Type of analysis (e.g., 'workout', 'weekly')
            input_data: The input data used for analysis
            result: The analysis result to cache
            model_name: The LLM model used
            tokens_used: Number of tokens used
            ttl_seconds: Time-to-live in seconds

        Returns:
            The created cache entry
        """
        cache_key = self.generate_cache_key(analysis_type, input_data)
        input_hash = self.generate_input_hash(input_data)

        entry = AnalysisCacheEntry(
            cache_key=cache_key,
            analysis_type=analysis_type,
            input_hash=input_hash,
            result=result,
            model_name=model_name,
            tokens_used=tokens_used,
        )

        self.set_cached(cache_key, entry, ttl_seconds)
        return entry

    def get_analysis(
        self,
        analysis_type: str,
        input_data: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a cached analysis result.

        Args:
            analysis_type: Type of analysis
            input_data: The input data (for cache key generation)

        Returns:
            The cached result if found and valid, None otherwise
        """
        cache_key = self.generate_cache_key(analysis_type, input_data)
        entry = self.get_cached(cache_key)

        if entry:
            # Verify input hash matches (data integrity check)
            expected_hash = self.generate_input_hash(input_data)
            if entry.input_hash == expected_hash:
                return entry.result

        return None

    def cleanup_expired(self) -> int:
        """
        Remove all expired cache entries.

        Returns:
            Number of entries removed
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM analysis_cache WHERE expires_at IS NOT NULL AND expires_at < ?",
                (datetime.now().isoformat(),)
            )
            return cursor.rowcount

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self._get_connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) as cnt FROM analysis_cache"
            ).fetchone()["cnt"]

            valid = conn.execute(
                "SELECT COUNT(*) as cnt FROM analysis_cache WHERE expires_at IS NULL OR expires_at > ?",
                (datetime.now().isoformat(),)
            ).fetchone()["cnt"]

            total_hits = conn.execute(
                "SELECT COALESCE(SUM(hit_count), 0) as hits FROM analysis_cache"
            ).fetchone()["hits"]

            total_tokens = conn.execute(
                "SELECT COALESCE(SUM(tokens_used), 0) as tokens FROM analysis_cache"
            ).fetchone()["tokens"]

            by_type = {}
            type_rows = conn.execute(
                "SELECT analysis_type, COUNT(*) as cnt FROM analysis_cache GROUP BY analysis_type"
            ).fetchall()
            for row in type_rows:
                by_type[row["analysis_type"]] = row["cnt"]

            return {
                "total_entries": total,
                "valid_entries": valid,
                "expired_entries": total - valid,
                "total_hits": total_hits,
                "total_tokens_saved": total_tokens * total_hits,  # Rough estimate
                "entries_by_type": by_type,
            }


# Singleton instance for dependency injection
_analysis_cache_repository: Optional[AnalysisCacheRepository] = None


def get_analysis_cache_repository() -> AnalysisCacheRepository:
    """Get or create the singleton AnalysisCacheRepository instance."""
    global _analysis_cache_repository
    if _analysis_cache_repository is None:
        _analysis_cache_repository = AnalysisCacheRepository()
    return _analysis_cache_repository
