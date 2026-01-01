"""Database module for training analyzer."""

from .database import TrainingDatabase
from .schema import SCHEMA
from .connection_pool import (
    SQLiteConnectionPool,
    get_connection_pool,
    close_default_pool,
)

__all__ = [
    "TrainingDatabase",
    "SCHEMA",
    "SQLiteConnectionPool",
    "get_connection_pool",
    "close_default_pool",
]
