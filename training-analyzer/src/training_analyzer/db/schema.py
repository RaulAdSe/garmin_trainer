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

-- Race goals table for tracking target races
CREATE TABLE IF NOT EXISTS race_goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    race_date TEXT NOT NULL,
    distance TEXT NOT NULL,
    target_time_sec INTEGER NOT NULL,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Weekly summaries for historical analysis
CREATE TABLE IF NOT EXISTS weekly_summaries (
    week_start TEXT PRIMARY KEY,
    total_distance_km REAL,
    total_duration_min REAL,
    total_load REAL,
    activity_count INTEGER,
    zone_distribution TEXT,  -- JSON with zone1_pct through zone5_pct
    ctl_start REAL,
    ctl_end REAL,
    ctl_change REAL,
    atl_change REAL,
    week_over_week_change REAL,
    is_recovery_week INTEGER DEFAULT 0,
    insights TEXT,           -- JSON array of insight strings
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for new tables
CREATE INDEX IF NOT EXISTS idx_race_goals_date ON race_goals(race_date);
CREATE INDEX IF NOT EXISTS idx_weekly_summaries_start ON weekly_summaries(week_start);

-- Insert default profile if not exists (using INSERT OR IGNORE)
INSERT OR IGNORE INTO user_profile (id, max_hr, rest_hr, threshold_hr, age, gender)
VALUES (1, 185, 55, 165, 30, 'male');
"""

# Separate schema for updating user profile
UPDATE_PROFILE_SQL = """
INSERT OR REPLACE INTO user_profile (id, max_hr, rest_hr, threshold_hr, age, gender, weight_kg, updated_at)
VALUES (1, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
"""
