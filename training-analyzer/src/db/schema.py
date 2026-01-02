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
    start_time TEXT,  -- Full ISO timestamp (e.g., "2024-01-15T07:30:00")
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
    -- Multi-sport extensions (Phase 2)
    sport_type TEXT,
    avg_power INTEGER,
    max_power INTEGER,
    normalized_power INTEGER,
    tss REAL,
    intensity_factor REAL,
    variability_index REAL,
    avg_speed_kmh REAL,
    elevation_gain_m REAL,
    cadence INTEGER,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Create index on date for efficient queries
CREATE INDEX IF NOT EXISTS idx_activity_metrics_date ON activity_metrics(date);
CREATE INDEX IF NOT EXISTS idx_fitness_metrics_date ON fitness_metrics(date);
CREATE INDEX IF NOT EXISTS idx_activity_metrics_sport_type ON activity_metrics(sport_type);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_activity_metrics_date_type ON activity_metrics(date, activity_type);

-- =============================================================================
-- Phase 2: Multi-sport Extensions - Power Zones Table
-- =============================================================================

-- Power zones for cycling/running power metrics
CREATE TABLE IF NOT EXISTS power_zones (
    athlete_id TEXT PRIMARY KEY,
    ftp INTEGER,
    zone1_max INTEGER,
    zone2_max INTEGER,
    zone3_max INTEGER,
    zone4_max INTEGER,
    zone5_max INTEGER,
    zone6_max INTEGER,
    zone7_max INTEGER,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- Phase 2: Multi-sport Extensions - Swim Metrics Table
-- =============================================================================

-- Swimming-specific metrics per activity
CREATE TABLE IF NOT EXISTS swim_metrics (
    activity_id TEXT PRIMARY KEY,
    pool_length_m INTEGER,
    total_strokes INTEGER,
    avg_swolf REAL,
    avg_stroke_rate REAL,
    css_pace_sec INTEGER,
    swim_pace_per_100m INTEGER,
    stroke_type TEXT,
    distance_per_stroke REAL,
    efficiency_index REAL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (activity_id) REFERENCES activity_metrics(activity_id)
);

-- Create index for swim metrics
CREATE INDEX IF NOT EXISTS idx_swim_metrics_activity ON swim_metrics(activity_id);

-- =============================================================================
-- Phase 2: Multi-sport Extensions - Swim Profile Table
-- =============================================================================

-- Swimmer profile for CSS and preferences (one per athlete)
CREATE TABLE IF NOT EXISTS swim_profile (
    athlete_id TEXT PRIMARY KEY DEFAULT 'default',
    -- Critical Swim Speed (threshold pace in sec/100m)
    css_pace INTEGER,
    css_pace_formatted TEXT,
    -- CSS test times for recalculation
    css_test_400m_sec REAL,
    css_test_200m_sec REAL,
    css_test_date TEXT,
    -- Pool preferences
    preferred_pool_length INTEGER DEFAULT 25,
    preferred_stroke TEXT DEFAULT 'freestyle',
    -- Swim-specific fitness metrics
    swim_ctl REAL DEFAULT 0.0,
    swim_atl REAL DEFAULT 0.0,
    -- Efficiency metrics by stroke (average SWOLF)
    freestyle_swolf REAL,
    backstroke_swolf REAL,
    breaststroke_swolf REAL,
    butterfly_swolf REAL,
    -- Zone paces (sec/100m)
    zone1_recovery_pace INTEGER,
    zone2_aerobic_pace INTEGER,
    zone3_threshold_pace INTEGER,
    zone4_vo2max_pace INTEGER,
    zone5_sprint_pace INTEGER,
    -- Metadata
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Create index for swim profile
CREATE INDEX IF NOT EXISTS idx_swim_profile_athlete ON swim_profile(athlete_id);

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

-- =============================================================================
-- Phase 1: Database Persistence - New Tables
-- =============================================================================

-- Structured workouts designed by the workout agent
CREATE TABLE IF NOT EXISTS workouts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    sport TEXT NOT NULL DEFAULT 'running',
    intervals_json TEXT NOT NULL,  -- JSON array of workout intervals
    estimated_duration_min INTEGER NOT NULL,
    estimated_distance_m INTEGER,
    estimated_load REAL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Index for efficient workout queries
CREATE INDEX IF NOT EXISTS idx_workouts_created_at ON workouts(created_at);
CREATE INDEX IF NOT EXISTS idx_workouts_sport ON workouts(sport);

-- Training plans generated by the plan agent
CREATE TABLE IF NOT EXISTS training_plans (
    id TEXT PRIMARY KEY,
    name TEXT,
    description TEXT,
    goal_json TEXT NOT NULL,           -- JSON object with race goal details
    periodization TEXT NOT NULL,        -- linear, reverse, block, undulating
    peak_week INTEGER NOT NULL,
    total_weeks INTEGER NOT NULL,
    weeks_json TEXT NOT NULL,          -- JSON array of training weeks
    athlete_context_json TEXT,         -- JSON object with athlete context
    constraints_json TEXT,             -- JSON object with plan constraints
    phases_summary_json TEXT,          -- JSON object with phase counts
    total_planned_load REAL,
    is_active INTEGER DEFAULT 0,
    adaptation_history_json TEXT,      -- JSON array of adaptations
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient plan queries
CREATE INDEX IF NOT EXISTS idx_training_plans_created_at ON training_plans(created_at);
CREATE INDEX IF NOT EXISTS idx_training_plans_is_active ON training_plans(is_active);
CREATE INDEX IF NOT EXISTS idx_training_plans_goal_race_date ON training_plans(json_extract(goal_json, '$.race_date'));

-- Workout analyses - permanent storage for AI-generated workout insights
CREATE TABLE IF NOT EXISTS workout_analyses (
    workout_id TEXT PRIMARY KEY,       -- References activity_metrics.activity_id
    summary TEXT NOT NULL,             -- Main analysis summary
    what_went_well TEXT,               -- JSON array of positive observations
    improvements TEXT,                 -- JSON array of areas for improvement
    training_context TEXT,             -- How workout fits into training
    execution_rating TEXT,             -- excellent, good, fair, needs_improvement
    overall_score INTEGER,             -- 0-100 overall score
    training_effect_score REAL,        -- Training effect (1.0-5.0)
    load_score INTEGER,                -- Load score (0-100+)
    recovery_hours INTEGER,            -- Recommended recovery time
    model_used TEXT,                   -- LLM model used for analysis
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Index for efficient queries
CREATE INDEX IF NOT EXISTS idx_workout_analyses_created ON workout_analyses(created_at);

-- =============================================================================
-- Garmin Fitness Data - VO2max, Race Predictions, Training Status
-- =============================================================================

-- Daily fitness data from Garmin (VO2max, race predictions, training status)
-- One record per day to track historical changes
CREATE TABLE IF NOT EXISTS garmin_fitness_data (
    date TEXT PRIMARY KEY,
    -- VO2max metrics
    vo2max_running REAL,           -- Running VO2max (precise value)
    vo2max_cycling REAL,           -- Cycling VO2max if available
    fitness_age INTEGER,           -- Garmin's fitness age estimate
    -- Race predictions (times in seconds)
    race_time_5k INTEGER,          -- 5K predicted time in seconds
    race_time_10k INTEGER,         -- 10K predicted time in seconds
    race_time_half INTEGER,        -- Half marathon predicted time in seconds
    race_time_marathon INTEGER,    -- Marathon predicted time in seconds
    -- Training status
    training_status TEXT,          -- PRODUCTIVE, UNPRODUCTIVE, PEAKING, RECOVERY, etc.
    training_status_description TEXT, -- Human-readable description
    fitness_trend TEXT,            -- IMPROVING, MAINTAINING, DECLINING
    -- Training readiness
    training_readiness_score INTEGER,  -- 0-100 readiness score
    training_readiness_level TEXT,     -- HIGH, MODERATE, LOW, POOR
    -- Acute:Chronic Workload Ratio
    acwr_percent REAL,             -- ACWR percentage
    acwr_status TEXT,              -- Status (OPTIMAL, HIGH_RISK, LOW, etc.)
    -- Metadata
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Create index for efficient date-based queries
CREATE INDEX IF NOT EXISTS idx_garmin_fitness_date ON garmin_fitness_data(date);

-- Insert default profile if not exists (using INSERT OR IGNORE)
INSERT OR IGNORE INTO user_profile (id, max_hr, rest_hr, threshold_hr, age, gender)
VALUES (1, 185, 55, 165, 30, 'male');

-- =============================================================================
-- Gamification System Tables
-- =============================================================================

-- Achievement definitions
CREATE TABLE IF NOT EXISTS achievements (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    icon TEXT NOT NULL,
    xp_value INTEGER NOT NULL DEFAULT 25,
    rarity TEXT DEFAULT 'common',
    condition_type TEXT,
    condition_value TEXT,
    display_order INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- User achievement unlocks
CREATE TABLE IF NOT EXISTS user_achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    achievement_id TEXT NOT NULL,
    unlocked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    workout_id TEXT,
    metadata_json TEXT,
    FOREIGN KEY (achievement_id) REFERENCES achievements(id),
    UNIQUE(achievement_id)
);

-- User progress tracking
CREATE TABLE IF NOT EXISTS user_progress (
    user_id TEXT PRIMARY KEY DEFAULT 'default',
    total_xp INTEGER DEFAULT 0,
    current_level INTEGER DEFAULT 1,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    streak_freeze_tokens INTEGER DEFAULT 0,
    last_activity_date TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for gamification tables
CREATE INDEX IF NOT EXISTS idx_user_achievements_unlocked ON user_achievements(unlocked_at);
CREATE INDEX IF NOT EXISTS idx_achievements_category ON achievements(category);
CREATE INDEX IF NOT EXISTS idx_user_progress_user_updated ON user_progress(user_id, updated_at);

-- =============================================================================
-- Strava Integration Tables
-- =============================================================================

-- Strava OAuth credentials storage
CREATE TABLE IF NOT EXISTS strava_credentials (
    user_id TEXT PRIMARY KEY DEFAULT 'default',
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    athlete_id TEXT,
    athlete_name TEXT,
    scope TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- User preferences for Strava integration
CREATE TABLE IF NOT EXISTS strava_preferences (
    user_id TEXT PRIMARY KEY DEFAULT 'default',
    auto_update_description BOOLEAN DEFAULT TRUE,
    include_score BOOLEAN DEFAULT TRUE,
    include_summary BOOLEAN DEFAULT TRUE,
    include_link BOOLEAN DEFAULT TRUE,
    use_extended_format BOOLEAN DEFAULT FALSE,
    custom_footer TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Activity mapping (local activity <-> Strava activity)
CREATE TABLE IF NOT EXISTS strava_activity_sync (
    local_activity_id TEXT PRIMARY KEY,
    strava_activity_id INTEGER NOT NULL,
    sync_status TEXT DEFAULT 'pending',
    last_synced_at TEXT,
    description_updated BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- OAuth state tokens for CSRF protection (database-backed for multi-instance support)
CREATE TABLE IF NOT EXISTS oauth_states (
    state TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for Strava tables
CREATE INDEX IF NOT EXISTS idx_strava_sync_status ON strava_activity_sync(sync_status);
CREATE INDEX IF NOT EXISTS idx_strava_activity ON strava_activity_sync(strava_activity_id);
CREATE INDEX IF NOT EXISTS idx_oauth_states_created ON oauth_states(created_at);

-- =============================================================================
-- Multi-User Authentication & Authorization Tables
-- =============================================================================

-- Core users table for multi-user support
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,                    -- UUID
    email TEXT UNIQUE NOT NULL,
    display_name TEXT,
    avatar_url TEXT,
    timezone TEXT DEFAULT 'UTC',
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Create index for user lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- User sessions for session-based authentication
CREATE TABLE IF NOT EXISTS user_sessions (
    id TEXT PRIMARY KEY,                    -- Session token
    user_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    user_agent TEXT,
    ip_address TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create indexes for session lookups
CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);

-- =============================================================================
-- Subscription & Billing Tables
-- =============================================================================

-- Subscription plan definitions
CREATE TABLE IF NOT EXISTS subscription_plans (
    id TEXT PRIMARY KEY,                    -- 'free', 'pro'
    name TEXT NOT NULL,
    price_cents INTEGER DEFAULT 0,          -- 0 for free, 999 for $9.99
    stripe_price_id TEXT,                   -- Stripe Price ID
    ai_analyses_per_month INTEGER,          -- NULL = unlimited
    ai_plans_limit INTEGER,
    ai_chat_messages_per_day INTEGER,
    ai_workouts_per_month INTEGER,
    history_days INTEGER,                   -- NULL = unlimited
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- User subscriptions linking users to plans
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id TEXT PRIMARY KEY,                    -- UUID
    user_id TEXT NOT NULL UNIQUE,
    plan_id TEXT NOT NULL DEFAULT 'free',
    status TEXT DEFAULT 'active',           -- 'active', 'canceled', 'past_due', 'trialing'
    stripe_customer_id TEXT UNIQUE,
    stripe_subscription_id TEXT UNIQUE,
    current_period_start TEXT,
    current_period_end TEXT,
    cancel_at_period_end INTEGER DEFAULT 0,
    trial_end TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES subscription_plans(id)
);

-- Create indexes for subscription lookups
CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON user_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON user_subscriptions(status);

-- User usage tracking per billing period
CREATE TABLE IF NOT EXISTS user_usage (
    id TEXT PRIMARY KEY,                    -- UUID
    user_id TEXT NOT NULL,
    period_start TEXT NOT NULL,             -- Start of billing period
    period_end TEXT NOT NULL,               -- End of billing period
    ai_analyses_used INTEGER DEFAULT 0,
    ai_chat_messages_used INTEGER DEFAULT 0,
    ai_workouts_generated INTEGER DEFAULT 0,
    ai_tokens_used INTEGER DEFAULT 0,
    ai_cost_cents INTEGER DEFAULT 0,        -- Cost tracking for analytics
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, period_start)
);

-- Create index for usage lookups
CREATE INDEX IF NOT EXISTS idx_user_usage_period ON user_usage(user_id, period_start DESC);

-- =============================================================================
-- Garmin Credential Storage & Sync Tables
-- =============================================================================

-- Encrypted Garmin credentials for auto-sync
CREATE TABLE IF NOT EXISTS garmin_credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL UNIQUE,
    encrypted_email TEXT NOT NULL,
    encrypted_password TEXT NOT NULL,
    encryption_key_id TEXT NOT NULL,        -- Reference for key rotation
    garmin_user_id TEXT,
    garmin_display_name TEXT,
    is_valid INTEGER DEFAULT 1,
    last_validation_at TEXT,
    validation_error TEXT,
    failed_validation_count INTEGER DEFAULT 0,  -- Track failed validation attempts for security
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create index for garmin credentials lookup
CREATE INDEX IF NOT EXISTS idx_garmin_creds_user ON garmin_credentials(user_id);

-- Garmin sync configuration per user
CREATE TABLE IF NOT EXISTS garmin_sync_config (
    user_id TEXT PRIMARY KEY,
    auto_sync_enabled INTEGER DEFAULT 1,
    sync_frequency TEXT DEFAULT 'daily',    -- 'hourly', 'daily', 'weekly'
    sync_time TEXT DEFAULT '06:00',         -- Preferred sync time (UTC)
    sync_activities INTEGER DEFAULT 1,
    sync_wellness INTEGER DEFAULT 1,
    sync_fitness_metrics INTEGER DEFAULT 1,
    initial_sync_days INTEGER DEFAULT 365,  -- First sync: 1 year back
    incremental_sync_days INTEGER DEFAULT 7,-- Subsequent: 7 days back
    min_sync_interval_minutes INTEGER DEFAULT 60,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Garmin sync history/audit log
CREATE TABLE IF NOT EXISTS garmin_sync_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    sync_type TEXT NOT NULL,                -- 'manual', 'scheduled', 'webhook'
    started_at TEXT NOT NULL,
    completed_at TEXT,
    duration_seconds INTEGER,
    status TEXT DEFAULT 'running',          -- 'running', 'completed', 'failed', 'partial'
    activities_synced INTEGER DEFAULT 0,
    wellness_days_synced INTEGER DEFAULT 0,
    fitness_days_synced INTEGER DEFAULT 0,
    sync_from_date TEXT,
    sync_to_date TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create indexes for sync history
CREATE INDEX IF NOT EXISTS idx_sync_history_user ON garmin_sync_history(user_id);
CREATE INDEX IF NOT EXISTS idx_sync_history_started ON garmin_sync_history(started_at DESC);

-- =============================================================================
-- User Consent Tracking
-- =============================================================================

-- User consent for LLM data sharing and privacy preferences
CREATE TABLE IF NOT EXISTS user_consent (
    user_id TEXT PRIMARY KEY,
    llm_data_sharing_consent INTEGER DEFAULT 0,  -- 0 = not consented, 1 = consented
    consent_date TEXT,                           -- ISO timestamp when consent was given/withdrawn
    consent_version TEXT DEFAULT 'v1',           -- Version of consent terms
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Create index for consent lookups
CREATE INDEX IF NOT EXISTS idx_user_consent_date ON user_consent(consent_date);

-- =============================================================================
-- Manual Workouts (RPE-based logging without device)
-- =============================================================================

-- Manual workouts logged via RPE without device data
CREATE TABLE IF NOT EXISTS manual_workouts (
    activity_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    activity_type TEXT DEFAULT 'running',
    date TEXT NOT NULL,
    duration_min INTEGER NOT NULL,
    distance_km REAL,
    rpe INTEGER NOT NULL CHECK (rpe >= 1 AND rpe <= 10),
    avg_hr INTEGER,
    max_hr INTEGER,
    estimated_load REAL NOT NULL,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create indexes for manual workouts
CREATE INDEX IF NOT EXISTS idx_manual_workouts_user ON manual_workouts(user_id);
CREATE INDEX IF NOT EXISTS idx_manual_workouts_date ON manual_workouts(date);
CREATE INDEX IF NOT EXISTS idx_manual_workouts_user_date ON manual_workouts(user_id, date);

-- =============================================================================
-- User Preferences (Beginner Mode, UI Settings)
-- =============================================================================

-- User preferences for UI customization and beginner mode
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id TEXT PRIMARY KEY,
    beginner_mode_enabled INTEGER DEFAULT 0,          -- 0 = disabled, 1 = enabled
    beginner_mode_start_date TEXT,                    -- ISO timestamp when beginner mode was enabled
    show_hr_metrics INTEGER DEFAULT 1,                -- Show heart rate metrics
    show_advanced_metrics INTEGER DEFAULT 1,          -- Show advanced metrics (CTL, ATL, TSB)
    preferred_intensity_scale TEXT DEFAULT 'hr',      -- 'hr', 'rpe', or 'pace'
    weekly_mileage_cap_enabled INTEGER DEFAULT 0,     -- Enable weekly mileage cap warnings
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create index for preferences lookups
CREATE INDEX IF NOT EXISTS idx_user_preferences_user ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_user_preferences_beginner ON user_preferences(beginner_mode_enabled);
"""

# Separate schema for updating user profile
UPDATE_PROFILE_SQL = """
INSERT OR REPLACE INTO user_profile (id, max_hr, rest_hr, threshold_hr, age, gender, weight_kg, updated_at)
VALUES (1, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
"""
