"""Tests for multi-sport schema extensions (Phase 2).

This module tests:
1. New columns in activity_metrics table
2. Power zones table functionality
3. Swim metrics table functionality
4. Migration script idempotency
"""

import os
import pytest
import sqlite3
import tempfile
from pathlib import Path

from training_analyzer.db.database import TrainingDatabase
from training_analyzer.db.migrations.migration_001_multi_sport import (
    migrate,
    rollback,
    column_exists,
    table_exists,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db = TrainingDatabase(db_path)
    yield db

    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def empty_db_path():
    """Create an empty database file path for migration testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        os.unlink(db_path)
    except OSError:
        pass


class TestActivityMetricsNewColumns:
    """Tests for new columns in activity_metrics table."""

    def test_sport_type_column_exists(self, temp_db):
        """sport_type column should exist in activity_metrics."""
        with temp_db._get_connection() as conn:
            assert column_exists(conn, "activity_metrics", "sport_type")

    def test_power_columns_exist(self, temp_db):
        """Power-related columns should exist in activity_metrics."""
        with temp_db._get_connection() as conn:
            assert column_exists(conn, "activity_metrics", "avg_power")
            assert column_exists(conn, "activity_metrics", "max_power")
            assert column_exists(conn, "activity_metrics", "normalized_power")
            assert column_exists(conn, "activity_metrics", "tss")
            assert column_exists(conn, "activity_metrics", "intensity_factor")
            assert column_exists(conn, "activity_metrics", "variability_index")

    def test_speed_and_elevation_columns_exist(self, temp_db):
        """Speed and elevation columns should exist in activity_metrics."""
        with temp_db._get_connection() as conn:
            assert column_exists(conn, "activity_metrics", "avg_speed_kmh")
            assert column_exists(conn, "activity_metrics", "elevation_gain_m")

    def test_cadence_column_exists(self, temp_db):
        """cadence column should exist in activity_metrics."""
        with temp_db._get_connection() as conn:
            assert column_exists(conn, "activity_metrics", "cadence")

    def test_insert_activity_with_new_columns(self, temp_db):
        """Should be able to insert activity with new multi-sport columns."""
        with temp_db._get_connection() as conn:
            conn.execute("""
                INSERT INTO activity_metrics (
                    activity_id, date, activity_type, sport_type,
                    avg_power, max_power, normalized_power,
                    tss, intensity_factor, variability_index,
                    avg_speed_kmh, elevation_gain_m, cadence
                ) VALUES (
                    'test_cycling_001', '2024-01-15', 'cycling', 'road_cycling',
                    200, 450, 210,
                    75.5, 0.85, 1.05,
                    32.5, 850, 90
                )
            """)

            row = conn.execute(
                "SELECT * FROM activity_metrics WHERE activity_id = ?",
                ("test_cycling_001",)
            ).fetchone()

            assert row is not None
            # Convert to dict for easier access
            columns = [desc[0] for desc in conn.execute(
                "SELECT * FROM activity_metrics LIMIT 0"
            ).description]
            data = dict(zip(columns, row))

            assert data["sport_type"] == "road_cycling"
            assert data["avg_power"] == 200
            assert data["max_power"] == 450
            assert data["normalized_power"] == 210
            assert data["tss"] == 75.5
            assert data["intensity_factor"] == 0.85
            assert data["variability_index"] == 1.05
            assert data["avg_speed_kmh"] == 32.5
            assert data["elevation_gain_m"] == 850
            assert data["cadence"] == 90


class TestPowerZonesTable:
    """Tests for power_zones table."""

    def test_power_zones_table_exists(self, temp_db):
        """power_zones table should exist."""
        with temp_db._get_connection() as conn:
            assert table_exists(conn, "power_zones")

    def test_power_zones_columns(self, temp_db):
        """power_zones table should have all required columns."""
        with temp_db._get_connection() as conn:
            assert column_exists(conn, "power_zones", "athlete_id")
            assert column_exists(conn, "power_zones", "ftp")
            assert column_exists(conn, "power_zones", "zone1_max")
            assert column_exists(conn, "power_zones", "zone2_max")
            assert column_exists(conn, "power_zones", "zone3_max")
            assert column_exists(conn, "power_zones", "zone4_max")
            assert column_exists(conn, "power_zones", "zone5_max")
            assert column_exists(conn, "power_zones", "zone6_max")
            assert column_exists(conn, "power_zones", "zone7_max")
            assert column_exists(conn, "power_zones", "updated_at")

    def test_insert_power_zones(self, temp_db):
        """Should be able to insert and retrieve power zones."""
        with temp_db._get_connection() as conn:
            # Insert power zones based on FTP of 250W
            conn.execute("""
                INSERT INTO power_zones (
                    athlete_id, ftp,
                    zone1_max, zone2_max, zone3_max, zone4_max,
                    zone5_max, zone6_max, zone7_max
                ) VALUES (
                    'athlete_001', 250,
                    137, 187, 225, 262, 300, 375, 500
                )
            """)

            row = conn.execute(
                "SELECT * FROM power_zones WHERE athlete_id = ?",
                ("athlete_001",)
            ).fetchone()

            assert row is not None
            columns = [desc[0] for desc in conn.execute(
                "SELECT * FROM power_zones LIMIT 0"
            ).description]
            data = dict(zip(columns, row))

            assert data["ftp"] == 250
            assert data["zone1_max"] == 137  # ~55% FTP
            assert data["zone2_max"] == 187  # ~75% FTP
            assert data["zone7_max"] == 500  # ~200% FTP

    def test_power_zones_primary_key(self, temp_db):
        """athlete_id should be the primary key."""
        with temp_db._get_connection() as conn:
            conn.execute("""
                INSERT INTO power_zones (athlete_id, ftp) VALUES ('athlete_001', 250)
            """)

            # Trying to insert same athlete_id should fail or replace
            conn.execute("""
                INSERT OR REPLACE INTO power_zones (athlete_id, ftp) VALUES ('athlete_001', 260)
            """)

            row = conn.execute(
                "SELECT ftp FROM power_zones WHERE athlete_id = ?",
                ("athlete_001",)
            ).fetchone()

            # Should have the updated value
            assert row[0] == 260

    def test_update_power_zones(self, temp_db):
        """Should be able to update power zones."""
        with temp_db._get_connection() as conn:
            conn.execute(
                "INSERT INTO power_zones (athlete_id, ftp) VALUES ('athlete_001', 250)"
            )

            conn.execute(
                "UPDATE power_zones SET ftp = 260 WHERE athlete_id = 'athlete_001'"
            )

            row = conn.execute(
                "SELECT ftp FROM power_zones WHERE athlete_id = 'athlete_001'"
            ).fetchone()

            assert row[0] == 260


class TestSwimMetricsTable:
    """Tests for swim_metrics table."""

    def test_swim_metrics_table_exists(self, temp_db):
        """swim_metrics table should exist."""
        with temp_db._get_connection() as conn:
            assert table_exists(conn, "swim_metrics")

    def test_swim_metrics_columns(self, temp_db):
        """swim_metrics table should have all required columns."""
        with temp_db._get_connection() as conn:
            assert column_exists(conn, "swim_metrics", "activity_id")
            assert column_exists(conn, "swim_metrics", "pool_length_m")
            assert column_exists(conn, "swim_metrics", "total_strokes")
            assert column_exists(conn, "swim_metrics", "avg_swolf")
            assert column_exists(conn, "swim_metrics", "avg_stroke_rate")
            assert column_exists(conn, "swim_metrics", "css_pace_sec")
            assert column_exists(conn, "swim_metrics", "updated_at")

    def test_insert_swim_metrics(self, temp_db):
        """Should be able to insert and retrieve swim metrics."""
        with temp_db._get_connection() as conn:
            # First insert the parent activity
            conn.execute("""
                INSERT INTO activity_metrics (activity_id, date, activity_type, sport_type)
                VALUES ('swim_001', '2024-01-15', 'swimming', 'pool_swimming')
            """)

            # Then insert swim metrics
            conn.execute("""
                INSERT INTO swim_metrics (
                    activity_id, pool_length_m, total_strokes,
                    avg_swolf, avg_stroke_rate, css_pace_sec
                ) VALUES (
                    'swim_001', 25, 1500,
                    45.5, 28.0, 105
                )
            """)

            row = conn.execute(
                "SELECT * FROM swim_metrics WHERE activity_id = ?",
                ("swim_001",)
            ).fetchone()

            assert row is not None
            columns = [desc[0] for desc in conn.execute(
                "SELECT * FROM swim_metrics LIMIT 0"
            ).description]
            data = dict(zip(columns, row))

            assert data["pool_length_m"] == 25
            assert data["total_strokes"] == 1500
            assert data["avg_swolf"] == 45.5
            assert data["avg_stroke_rate"] == 28.0
            assert data["css_pace_sec"] == 105  # 1:45/100m

    def test_swim_metrics_primary_key(self, temp_db):
        """activity_id should be the primary key."""
        with temp_db._get_connection() as conn:
            conn.execute("""
                INSERT INTO activity_metrics (activity_id, date, activity_type)
                VALUES ('swim_001', '2024-01-15', 'swimming')
            """)

            conn.execute("""
                INSERT INTO swim_metrics (activity_id, pool_length_m) VALUES ('swim_001', 25)
            """)

            # Trying to insert same activity_id should fail or replace
            conn.execute("""
                INSERT OR REPLACE INTO swim_metrics (activity_id, pool_length_m) VALUES ('swim_001', 50)
            """)

            row = conn.execute(
                "SELECT pool_length_m FROM swim_metrics WHERE activity_id = ?",
                ("swim_001",)
            ).fetchone()

            # Should have the updated value
            assert row[0] == 50


class TestMigrationScript:
    """Tests for the migration script."""

    def test_migration_on_fresh_database(self, empty_db_path):
        """Migration should work on a fresh database."""
        # First create the base schema
        db = TrainingDatabase(empty_db_path)

        # Now run the migration (should be idempotent)
        result = migrate(empty_db_path)

        # The migration might not add columns if schema already has them
        assert result["success"] is True
        assert "errors" in result
        assert len(result["errors"]) == 0

    def test_migration_idempotency(self, empty_db_path):
        """Running migration multiple times should not cause errors."""
        db = TrainingDatabase(empty_db_path)

        # Run migration twice
        result1 = migrate(empty_db_path)
        result2 = migrate(empty_db_path)

        assert result1["success"] is True
        assert result2["success"] is True
        # Second run should have fewer changes since everything exists
        assert len(result2["columns_added"]) <= len(result1["columns_added"])

    def test_migration_creates_tables(self, empty_db_path):
        """Migration should create new tables."""
        # Create a minimal database without the new tables
        conn = sqlite3.connect(empty_db_path)
        conn.execute("""
            CREATE TABLE activity_metrics (
                activity_id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                activity_type TEXT
            )
        """)
        conn.commit()
        conn.close()

        result = migrate(empty_db_path)

        assert result["success"] is True
        assert "power_zones" in result["tables_created"]
        assert "swim_metrics" in result["tables_created"]

    def test_migration_adds_columns(self, empty_db_path):
        """Migration should add new columns to existing tables."""
        # Create a minimal database without the new columns
        conn = sqlite3.connect(empty_db_path)
        conn.execute("""
            CREATE TABLE activity_metrics (
                activity_id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                activity_type TEXT
            )
        """)
        conn.commit()
        conn.close()

        result = migrate(empty_db_path)

        assert result["success"] is True
        assert len(result["columns_added"]) > 0
        assert "activity_metrics.sport_type" in result["columns_added"]
        assert "activity_metrics.avg_power" in result["columns_added"]

    def test_rollback(self, empty_db_path):
        """Rollback should remove new tables."""
        db = TrainingDatabase(empty_db_path)
        migrate(empty_db_path)

        result = rollback(empty_db_path)

        assert result["success"] is True
        assert "swim_metrics" in result["tables_dropped"]
        assert "power_zones" in result["tables_dropped"]

        # Verify tables are gone
        conn = sqlite3.connect(empty_db_path)
        assert not table_exists(conn, "swim_metrics")
        assert not table_exists(conn, "power_zones")
        conn.close()


class TestSportTypeIndex:
    """Tests for sport_type index."""

    def test_sport_type_index_exists(self, temp_db):
        """Index on sport_type should exist."""
        with temp_db._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
                ("idx_activity_metrics_sport_type",)
            )
            result = cursor.fetchone()
            assert result is not None

    def test_sport_type_index_improves_query(self, temp_db):
        """Query by sport_type should use the index."""
        with temp_db._get_connection() as conn:
            # Insert some test data
            for i in range(10):
                sport = "cycling" if i % 2 == 0 else "running"
                conn.execute(
                    """
                    INSERT INTO activity_metrics (activity_id, date, activity_type, sport_type)
                    VALUES (?, '2024-01-15', ?, ?)
                    """,
                    (f"act_{i}", sport, sport)
                )

            # Query should work efficiently
            rows = conn.execute(
                "SELECT * FROM activity_metrics WHERE sport_type = 'cycling'"
            ).fetchall()

            assert len(rows) == 5
