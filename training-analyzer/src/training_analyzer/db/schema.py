"""Database schema for training metrics."""

SCHEMA = """
-- User profile for personalized calculations
CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY DEFAULT 1,
    max_hr INTEGER,
    rest_hr INTEGER,
    threshold_hr INTEGER,
    gender TEXT DEFAULT 'male',
    age INTEGER,
    weight_kg REAL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Daily fitness metrics (one row per day)
CREATE TABLE IF NOT EXISTS fitness_metrics (
    date TEXT PRIMARY KEY,
    daily_load REAL,
    ctl REAL,
    atl REAL,
    tsb REAL,
    acwr REAL,
    risk_zone TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Enriched activity data (supplements n8n raw_activities)
CREATE TABLE IF NOT EXISTS activity_metrics (
    activity_id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    activity_type TEXT,
    activity_name TEXT,
    hrss REAL,
    trimp REAL,
    avg_hr INTEGER,
    max_hr INTEGER,
    duration_min REAL,
    distance_km REAL,
    pace_sec_per_km REAL,
    zone1_pct REAL,
    zone2_pct REAL,
    zone3_pct REAL,
    zone4_pct REAL,
    zone5_pct REAL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Create index on date for efficient queries
CREATE INDEX IF NOT EXISTS idx_activity_metrics_date ON activity_metrics(date);
CREATE INDEX IF NOT EXISTS idx_fitness_metrics_date ON fitness_metrics(date);

-- Insert default profile if not exists (using INSERT OR IGNORE)
INSERT OR IGNORE INTO user_profile (id, max_hr, rest_hr, threshold_hr, age, gender)
VALUES (1, 185, 55, 165, 30, 'male');
"""

# Separate schema for updating user profile
UPDATE_PROFILE_SQL = """
INSERT OR REPLACE INTO user_profile (id, max_hr, rest_hr, threshold_hr, age, gender, weight_kg, updated_at)
VALUES (1, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
"""
