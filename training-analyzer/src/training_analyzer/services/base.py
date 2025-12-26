"""
Base service classes and protocols.

Defines the interfaces and base classes for all services.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Protocol, TypeVar, runtime_checkable
from datetime import datetime
import logging

from pydantic import BaseModel


# Type variables for generic repository pattern
T = TypeVar("T", bound=BaseModel)
ID = TypeVar("ID")


@runtime_checkable
class Repository(Protocol[T, ID]):
    """
    Protocol defining the interface for data repositories.

    Implementations should provide CRUD operations for a specific entity type.
    """

    async def get(self, id: ID) -> Optional[T]:
        """Get entity by ID."""
        ...

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[T]:
        """Get all entities with optional filtering and pagination."""
        ...

    async def create(self, entity: T) -> T:
        """Create a new entity."""
        ...

    async def update(self, id: ID, entity: T) -> T:
        """Update an existing entity."""
        ...

    async def delete(self, id: ID) -> bool:
        """Delete an entity by ID."""
        ...

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities with optional filtering."""
        ...


@runtime_checkable
class CacheProtocol(Protocol):
    """Protocol for cache implementations."""

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        ...

    async def set(
        self,
        key: str,
        value: Any,
        expire_seconds: Optional[int] = None,
    ) -> None:
        """Set value in cache."""
        ...

    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        ...


class BaseService(ABC):
    """
    Abstract base class for all services.

    Provides common functionality:
    - Logging setup
    - Cache integration
    - Error handling utilities
    """

    def __init__(
        self,
        cache: Optional[CacheProtocol] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._cache = cache
        self._logger = logger or logging.getLogger(self.__class__.__name__)

    @property
    def logger(self) -> logging.Logger:
        """Get the logger instance."""
        return self._logger

    @property
    def cache(self) -> Optional[CacheProtocol]:
        """Get the cache instance."""
        return self._cache

    async def _get_from_cache(
        self,
        key: str,
        default: Optional[T] = None,
    ) -> Optional[T]:
        """Get value from cache with fallback to default."""
        if self._cache is None:
            return default
        try:
            value = await self._cache.get(key)
            return value if value is not None else default
        except Exception as e:
            self._logger.warning(f"Cache get failed for key '{key}': {e}")
            return default

    async def _set_in_cache(
        self,
        key: str,
        value: Any,
        expire_seconds: Optional[int] = None,
    ) -> None:
        """Set value in cache, handling errors gracefully."""
        if self._cache is None:
            return
        try:
            await self._cache.set(key, value, expire_seconds)
        except Exception as e:
            self._logger.warning(f"Cache set failed for key '{key}': {e}")

    async def _delete_from_cache(self, key: str) -> None:
        """Delete value from cache, handling errors gracefully."""
        if self._cache is None:
            return
        try:
            await self._cache.delete(key)
        except Exception as e:
            self._logger.warning(f"Cache delete failed for key '{key}': {e}")


class PaginationParams(BaseModel):
    """Standard pagination parameters."""

    page: int = 1
    page_size: int = 20
    sort_by: Optional[str] = None
    sort_order: str = "desc"

    @property
    def offset(self) -> int:
        """Calculate offset from page and page_size."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Alias for page_size."""
        return self.page_size


class PaginatedResult(BaseModel, Generic[T]):
    """Standard paginated response wrapper."""

    items: List[T]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        """Calculate total pages."""
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        """Check if there are more pages."""
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        """Check if there are previous pages."""
        return self.page > 1

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True


class ServiceResult(BaseModel, Generic[T]):
    """
    Wrapper for service operation results.

    Provides a consistent way to return success/failure status
    along with optional data and error messages.
    """

    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def ok(
        cls,
        data: T,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ServiceResult[T]":
        """Create a successful result."""
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def fail(
        cls,
        error: str,
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ServiceResult[T]":
        """Create a failed result."""
        return cls(
            success=False,
            error=error,
            error_code=error_code,
            metadata=metadata,
        )

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True
