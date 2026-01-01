# Supabase Migration Guide

This document describes the migration path from SQLite to Supabase (PostgreSQL) for production deployment.

## Overview

The Training Analyzer is designed to migrate from SQLite (development) to Supabase (production):

| Feature | SQLite | Supabase |
|---------|--------|----------|
| Deployment | Local file | Cloud hosted |
| Scaling | Single user | Multi-user |
| Concurrency | Limited | Excellent |
| Security | File-based | Row-Level Security |
| Backup | Manual | Automatic |
| Auth | Custom JWT | Supabase Auth |

## Migration Strategy

### Phase 1: Adapter Pattern (✅ Complete)

The adapter pattern enables switching databases without code changes:

```
src/db/adapters/
├── __init__.py          # DatabaseAdapter ABC
├── sqlite_adapter.py    # SQLite implementation
└── supabase_adapter.py  # PostgreSQL implementation
```

Usage:
```python
# Development (SQLite)
from training_analyzer.db.adapters import SQLiteAdapter
adapter = SQLiteAdapter(db_path="training.db")

# Production (Supabase)
from training_analyzer.db.adapters import SupabaseAdapter
adapter = SupabaseAdapter(url=SUPABASE_URL, key=SUPABASE_KEY)

# Same interface
activities = adapter.get_activities_range(start, end, user_id=user_id)
```

### Phase 2: Schema Migration

Create PostgreSQL schema in Supabase. Key differences:

| SQLite | PostgreSQL |
|--------|------------|
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `SERIAL PRIMARY KEY` |
| `INTEGER` (boolean) | `BOOLEAN` |
| `TEXT` (datetime) | `TIMESTAMPTZ` |
| `TEXT` (date) | `DATE` |
| `INSERT OR REPLACE` | `INSERT ... ON CONFLICT` |
| `datetime('now')` | `NOW()` |

### Phase 3: Data Migration

Run the migration script to transfer data:

```bash
# Preview migration
python scripts/migrate_to_supabase.py --dry-run

# Full migration
python scripts/migrate_to_supabase.py

# Migrate specific tables
python scripts/migrate_to_supabase.py --tables activity_metrics,fitness_metrics
```

### Phase 4: Enable RLS

Set up Row-Level Security for multi-tenant isolation.

## Environment Setup

### Supabase Project

1. Create project at [supabase.com](https://supabase.com)
2. Get credentials from Settings > API
3. Configure `.env`:

```bash
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...    # Public key
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIs... # Service key (backend only)
DATABASE_BACKEND=supabase
```

## PostgreSQL Schema

Generate the schema:

```bash
python scripts/migrate_to_supabase.py --generate-schema > schema.sql
```

Key tables with PostgreSQL syntax:

### Users Table

```sql
CREATE TABLE public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    display_name TEXT,
    avatar_url TEXT,
    timezone TEXT DEFAULT 'UTC',
    max_hr INTEGER,
    rest_hr INTEGER,
    threshold_hr INTEGER,
    subscription_tier TEXT DEFAULT 'free',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Activity Metrics Table

```sql
CREATE TABLE public.activity_metrics (
    activity_id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    start_time TIMESTAMPTZ,
    activity_type TEXT,
    hrss DOUBLE PRECISION,
    trimp DOUBLE PRECISION,
    -- ... other columns
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX idx_activity_user_date ON activity_metrics(user_id, date DESC);
CREATE INDEX idx_activity_type ON activity_metrics(activity_type);
```

## Row-Level Security (RLS)

Enable RLS for multi-tenant data isolation:

```sql
-- Enable RLS on table
ALTER TABLE public.activity_metrics ENABLE ROW LEVEL SECURITY;

-- Users can only see their own activities
CREATE POLICY "Users can view own activities"
    ON public.activity_metrics
    FOR SELECT
    USING (auth.uid() = user_id);

-- Users can only insert their own activities
CREATE POLICY "Users can insert own activities"
    ON public.activity_metrics
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can only update their own activities
CREATE POLICY "Users can update own activities"
    ON public.activity_metrics
    FOR UPDATE
    USING (auth.uid() = user_id);

-- Users can only delete their own activities
CREATE POLICY "Users can delete own activities"
    ON public.activity_metrics
    FOR DELETE
    USING (auth.uid() = user_id);
```

## Migration Script

The migration script (`scripts/migrate_to_supabase.py`) handles:

1. **Data Transformation**: Converts SQLite types to PostgreSQL
2. **Boolean Conversion**: `INTEGER 0/1` → `BOOLEAN`
3. **Timestamp Handling**: Ensures ISO format with timezone
4. **User ID Assignment**: Adds `user_id` for multi-tenant tables
5. **Batch Processing**: Configurable batch sizes for large tables
6. **Error Handling**: Row-by-row retry on batch failures

### Usage

```bash
# Full migration
python scripts/migrate_to_supabase.py

# Options
python scripts/migrate_to_supabase.py --help

Options:
  --dry-run           Preview migration without writing
  --tables TEXT       Comma-separated list of tables
  --batch-size INT    Rows per batch (default: 100)
  --sqlite-path TEXT  Path to SQLite database
  --user-id TEXT      User ID for single-user data (default: "default")
  --generate-schema   Output PostgreSQL schema and exit
  --output TEXT       Output file for results
```

### Migration Order

Tables are migrated in dependency order:

1. `users`
2. `subscription_plans`
3. `user_subscriptions`
4. `user_usage`
5. `user_profile`
6. `activity_metrics`
7. `fitness_metrics`
8. ... (other tables)

## Supabase Auth Integration

Replace custom JWT auth with Supabase Auth:

### Before (Custom JWT)
```python
from training_analyzer.services.auth_service import verify_token

payload = verify_token(token)
user_id = payload["sub"]
```

### After (Supabase Auth)
```python
from supabase import create_client

supabase = create_client(url, key)
user = supabase.auth.get_user(token)
user_id = user.user.id
```

### OAuth Providers

Configure in Supabase Dashboard > Authentication > Providers:

- Google OAuth
- Apple Sign In
- Email/Password

## API Changes

### Pagination

SQLite uses `LIMIT/OFFSET`:
```sql
SELECT * FROM activities LIMIT 20 OFFSET 40
```

Supabase client uses `range()`:
```python
supabase.table("activities").select("*").range(40, 59).execute()
```

### Upsert

SQLite:
```sql
INSERT OR REPLACE INTO activities (id, ...) VALUES (?, ...)
```

PostgreSQL:
```sql
INSERT INTO activities (id, ...) VALUES ($1, ...)
ON CONFLICT (id) DO UPDATE SET
    date = EXCLUDED.date,
    ...
```

Supabase client:
```python
supabase.table("activities").upsert(data, on_conflict="id").execute()
```

## Testing the Migration

1. **Dry Run**: Preview without changes
   ```bash
   python scripts/migrate_to_supabase.py --dry-run
   ```

2. **Test Table**: Migrate a small table first
   ```bash
   python scripts/migrate_to_supabase.py --tables user_profile
   ```

3. **Verify Data**: Check row counts match
   ```sql
   SELECT COUNT(*) FROM activity_metrics;
   ```

4. **Test Queries**: Run application queries against Supabase

5. **Full Migration**: Migrate all tables
   ```bash
   python scripts/migrate_to_supabase.py
   ```

## Rollback Plan

If migration fails:

1. **Keep SQLite**: Don't delete SQLite database
2. **Revert Config**: Set `DATABASE_BACKEND=sqlite`
3. **Drop Tables**: Clean up Supabase tables if needed
4. **Fix Issues**: Address migration errors
5. **Retry**: Re-run migration

## Performance Considerations

### Indexes

Add these indexes in Supabase:

```sql
-- Pagination queries
CREATE INDEX idx_activity_user_date ON activity_metrics(user_id, date DESC);

-- Filter queries
CREATE INDEX idx_activity_type ON activity_metrics(activity_type);
CREATE INDEX idx_activity_sport ON activity_metrics(sport_type);

-- Covering index for list queries
CREATE INDEX idx_activity_list ON activity_metrics(
    user_id, date DESC, activity_id, activity_type, hrss
);
```

### Connection Pooling

Supabase handles connection pooling via PgBouncer. No additional configuration needed.

### Caching

Consider adding Redis caching for frequently accessed data:
- User profiles
- Subscription status
- Feature limits

## Checklist

Pre-migration:
- [ ] Create Supabase project
- [ ] Configure environment variables
- [ ] Run schema migration
- [ ] Enable RLS policies
- [ ] Test with dry-run

Migration:
- [ ] Backup SQLite database
- [ ] Run migration script
- [ ] Verify row counts
- [ ] Test application queries
- [ ] Enable Supabase Auth

Post-migration:
- [ ] Monitor for errors
- [ ] Check query performance
- [ ] Verify RLS working
- [ ] Update deployment config

## Related Documentation

- [MULTI_USER_ARCHITECTURE.md](./MULTI_USER_ARCHITECTURE.md) - System overview
- [DATABASE_SCALING_PLAN.md](./DATABASE_SCALING_PLAN.md) - Original scaling plan
- [REPOSITORY_LAYER.md](./REPOSITORY_LAYER.md) - Repository documentation
