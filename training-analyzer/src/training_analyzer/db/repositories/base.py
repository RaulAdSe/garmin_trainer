"""Base repository interfaces and abstract classes.

Provides abstract base classes for implementing the Repository pattern,
supporting both synchronous and asynchronous operations.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Dict, Any

# Type variable for the entity type stored in the repository
T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """
    Abstract base class for synchronous repository implementations.

    Provides a standard interface for CRUD operations on entities,
    abstracting away the underlying storage mechanism.

    Type Parameters:
        T: The type of entity stored in this repository
    """

    @abstractmethod
    def save(self, entity: T) -> T:
        """
        Save an entity to the repository.

        If the entity already exists (by ID), it will be updated.
        Otherwise, a new entity will be created.

        Args:
            entity: The entity to save

        Returns:
            The saved entity (may include generated fields)
        """
        pass

    @abstractmethod
    def get(self, entity_id: str) -> Optional[T]:
        """
        Retrieve an entity by its ID.

        Args:
            entity_id: The unique identifier of the entity

        Returns:
            The entity if found, None otherwise
        """
        pass

    @abstractmethod
    def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        **filters
    ) -> List[T]:
        """
        Retrieve all entities matching the given filters.

        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip
            **filters: Additional filter criteria

        Returns:
            List of matching entities
        """
        pass

    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """
        Delete an entity by its ID.

        Args:
            entity_id: The unique identifier of the entity to delete

        Returns:
            True if the entity was deleted, False if not found
        """
        pass

    @abstractmethod
    def exists(self, entity_id: str) -> bool:
        """
        Check if an entity exists by its ID.

        Args:
            entity_id: The unique identifier to check

        Returns:
            True if the entity exists, False otherwise
        """
        pass

    @abstractmethod
    def count(self, **filters) -> int:
        """
        Count entities matching the given filters.

        Args:
            **filters: Filter criteria

        Returns:
            Number of matching entities
        """
        pass


class AsyncRepository(ABC, Generic[T]):
    """
    Abstract base class for asynchronous repository implementations.

    Provides the same interface as Repository but with async methods
    for use with async/await patterns.

    Type Parameters:
        T: The type of entity stored in this repository
    """

    @abstractmethod
    async def save(self, entity: T) -> T:
        """Save an entity asynchronously."""
        pass

    @abstractmethod
    async def get(self, entity_id: str) -> Optional[T]:
        """Retrieve an entity by ID asynchronously."""
        pass

    @abstractmethod
    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        **filters
    ) -> List[T]:
        """Retrieve all matching entities asynchronously."""
        pass

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete an entity by ID asynchronously."""
        pass

    @abstractmethod
    async def exists(self, entity_id: str) -> bool:
        """Check if an entity exists asynchronously."""
        pass

    @abstractmethod
    async def count(self, **filters) -> int:
        """Count matching entities asynchronously."""
        pass


class CachingRepository(Repository[T]):
    """
    Base class for repositories that support caching.

    Provides additional methods for cache management.
    """

    @abstractmethod
    def get_cached(self, cache_key: str) -> Optional[T]:
        """
        Retrieve an entity from cache.

        Args:
            cache_key: The cache key to look up

        Returns:
            The cached entity if found and not expired, None otherwise
        """
        pass

    @abstractmethod
    def set_cached(
        self,
        cache_key: str,
        entity: T,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Store an entity in cache.

        Args:
            cache_key: The cache key to store under
            entity: The entity to cache
            ttl_seconds: Time-to-live in seconds (None for default)
        """
        pass

    @abstractmethod
    def invalidate_cache(self, cache_key: str) -> bool:
        """
        Invalidate a cache entry.

        Args:
            cache_key: The cache key to invalidate

        Returns:
            True if the entry was invalidated, False if not found
        """
        pass

    @abstractmethod
    def clear_cache(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        pass
