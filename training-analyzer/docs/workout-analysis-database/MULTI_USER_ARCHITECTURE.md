# Multi-User Architecture

This document describes the multi-user architecture implemented for the Training Analyzer application, enabling support for multiple users with subscription-based feature access.

## Overview

The multi-user architecture was implemented following the [DATABASE_SCALING_PLAN.md](./DATABASE_SCALING_PLAN.md) specification. It provides:

- **User Management**: User accounts with authentication and sessions
- **Subscription Tiers**: Free and Pro plans with usage limits
- **Feature Gating**: Restrict AI features based on subscription tier
- **Multi-tenant Data**: All user data isolated by `user_id`
- **Garmin Integration**: Encrypted credential storage per user
- **AI Usage Tracking**: Per-user cost and usage monitoring

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API Layer                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   /auth/*    │  │  /workouts/* │  │   /ai/*      │  │  /garmin/*   │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
└─────────┼─────────────────┼─────────────────┼─────────────────┼────────────┘
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Service Layer                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ AuthService  │  │ FeatureGate  │  │ AIUsageLog   │  │GarminScheduler│   │
│  │  - JWT Auth  │  │  - Limits    │  │  - Tracking  │  │  - Auto Sync │    │
│  │  - Sessions  │  │  - Tiers     │  │  - Costs     │  │  - Encryption│    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
└─────────┼─────────────────┼─────────────────┼─────────────────┼────────────┘
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Repository Layer                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │    User      │  │ Subscription │  │   AIUsage    │  │   Garmin     │    │
│  │  Repository  │  │  Repository  │  │  Repository  │  │  Repository  │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
└─────────┼─────────────────┼─────────────────┼─────────────────┼────────────┘
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Database Layer                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      SQLite / Supabase                               │   │
│  │  ┌─────────┐ ┌─────────────────┐ ┌─────────────┐ ┌───────────────┐  │   │
│  │  │  users  │ │user_subscriptions│ │ai_usage_logs│ │garmin_credentials│ │   │
│  │  └─────────┘ └─────────────────┘ └─────────────┘ └───────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Database Schema

### New Tables Created

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `users` | User accounts | `id`, `email`, `display_name`, `timezone` |
| `user_sessions` | JWT session tracking | `user_id`, `expires_at`, `ip_address` |
| `subscription_plans` | Plan definitions | `id`, `name`, `price_cents`, AI limits |
| `user_subscriptions` | User plan mappings | `user_id`, `plan_id`, `stripe_*` |
| `user_usage` | Monthly usage tracking | `user_id`, `ai_analyses_used`, `ai_cost_cents` |
| `garmin_credentials` | Encrypted Garmin login | `user_id`, `encrypted_email/password` |
| `garmin_sync_config` | Per-user sync settings | `user_id`, `auto_sync_enabled`, `sync_frequency` |
| `garmin_sync_history` | Sync job history | `user_id`, `status`, `activities_synced` |
| `ai_usage_logs` | Detailed AI request logs | `user_id`, `model_id`, `tokens`, `cost_cents` |

### Multi-tenant Columns Added

The following existing tables now include a `user_id` column:

- `activity_metrics`
- `fitness_metrics`
- `workouts`
- `training_plans`
- `workout_analyses`
- `garmin_fitness_data`
- `race_goals`
- `weekly_summaries`

## Subscription Tiers

### Free Tier
| Feature | Limit |
|---------|-------|
| AI Analyses | 5/month |
| AI Training Plans | 1 active |
| AI Chat Messages | 10/day |
| AI Workouts | 3/month |
| History Access | 180 days |
| Data Export | Not available |
| Priority Sync | Not available |

### Pro Tier ($9.99/month)
| Feature | Limit |
|---------|-------|
| AI Analyses | Unlimited |
| AI Training Plans | Unlimited |
| AI Chat Messages | Unlimited |
| AI Workouts | Unlimited |
| History Access | Unlimited |
| Data Export | Available |
| Priority Sync | Available |

## File Structure

```
training-analyzer/src/
├── db/
│   ├── migrations/
│   │   ├── migration_003_multi_user.py    # Schema migration
│   │   └── migration_004_performance.py   # Performance indexes
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base.py                        # BaseRepository class
│   │   ├── user_repository.py             # User CRUD
│   │   ├── subscription_repository.py     # Plans & usage
│   │   ├── garmin_credentials_repository.py
│   │   └── ai_usage_repository.py
│   ├── adapters/
│   │   ├── __init__.py                    # DatabaseAdapter ABC
│   │   ├── sqlite_adapter.py              # SQLite implementation
│   │   └── supabase_adapter.py            # PostgreSQL (Supabase)
│   ├── connection_pool.py                 # SQLiteConnectionPool
│   └── database.py                        # TrainingDatabase
├── services/
│   ├── auth_service.py                    # JWT authentication
│   ├── feature_gate.py                    # Subscription limits
│   ├── encryption.py                      # Credential encryption
│   └── garmin_scheduler.py                # Auto-sync scheduler
└── api/routes/
    └── stripe_webhook.py                  # Stripe subscription webhooks
```

## Usage Examples

### Creating a User
```python
from training_analyzer.db.repositories import get_user_repository

user_repo = get_user_repository()
user = user_repo.create_user(
    user_id="usr_123",
    email="athlete@example.com",
    display_name="John Doe",
    timezone="America/New_York"
)
```

### Checking Feature Access
```python
from training_analyzer.services.feature_gate import check_and_increment, Feature

# Raises HTTP 402 if limit reached
check_and_increment(user_id, Feature.AI_ANALYSIS, subscription_tier)
```

### Logging AI Usage
```python
from training_analyzer.db.repositories import get_ai_usage_repository

ai_repo = get_ai_usage_repository()
ai_repo.log_usage(
    request_id=str(uuid.uuid4()),
    user_id=user_id,
    model_id="gpt-4o-mini",
    input_tokens=1000,
    output_tokens=500,
    analysis_type="workout_analysis"
)
```

## Migration Path

The system is designed to migrate from SQLite to Supabase/PostgreSQL:

1. **Current**: SQLite with WAL mode for development
2. **Future**: Supabase with Row-Level Security for production

See [SUPABASE_MIGRATION.md](./SUPABASE_MIGRATION.md) for the migration guide.

## Related Documentation

- [DATABASE_SCALING_PLAN.md](./DATABASE_SCALING_PLAN.md) - Original scaling plan
- [REPOSITORY_LAYER.md](./REPOSITORY_LAYER.md) - Repository documentation
- [AUTHENTICATION.md](./AUTHENTICATION.md) - JWT auth details
- [FEATURE_GATING.md](./FEATURE_GATING.md) - Subscription limits
- [GARMIN_SYNC.md](./GARMIN_SYNC.md) - Garmin integration
- [AI_USAGE_TRACKING.md](./AI_USAGE_TRACKING.md) - Cost tracking
- [TESTING.md](./TESTING.md) - Test coverage
