# Database Scaling & Multi-User Production Plan

> **Generated**: December 29, 2025
> **Status**: Implementation Ready
> **Priority**: High

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Authentication Strategy](#authentication-strategy)
4. [Multi-User Architecture](#multi-user-architecture)
5. [Stripe Payments & Subscriptions](#stripe-payments--subscriptions)
6. [AI Cost Tracking System](#ai-cost-tracking-system)
7. [Garmin Auto-Sync with Credential Storage](#garmin-auto-sync-with-credential-storage)
8. [Performance Optimization](#performance-optimization)
9. [Deployment Strategy](#deployment-strategy)
10. [Implementation Roadmap](#implementation-roadmap)

---

## Executive Summary

This document outlines the complete plan to transform the garmin_insights Training Analyzer from a single-user SQLite application to a production-ready, multi-user SaaS platform with:

- **Google OAuth authentication** for app login
- **Multi-tenant database architecture** with user isolation
- **Stripe payments & subscriptions** (Free + Pro tiers)
- **AI usage tracking and billing** with rate limiting
- **Automatic Garmin Connect sync** with secure credential storage
- **Strava OAuth integration** for additional data sync
- **Performance optimizations** for scale
- **Production deployment** on Supabase (PostgreSQL)

### Current vs Target State

| Component | Current | Target |
|-----------|---------|--------|
| Database | SQLite (local) | **Supabase PostgreSQL** (cloud) |
| App Auth | None | **Google OAuth** (via Supabase Auth) |
| Data Sources | Manual | **Garmin** (encrypted) + **Strava** (OAuth) |
| Payments | None | **Stripe** (Free + Pro subscriptions) |
| AI Tracking | In-memory only | Persistent with usage limits |
| Management | Manual SQL | **Claude Code Supabase MCP** |

### Migration Strategy

**Phase 1 (Current)**: SQLite locally for development
**Phase 2 (Future)**: Migrate to Supabase (PostgreSQL) using Claude Code's Supabase MCP

### Supabase Free Tier Limits

| Resource | Free Limit |
|----------|------------|
| Database Size | 500 MB |
| Bandwidth | 5 GB |
| Storage | 1 GB |
| Edge Functions | 500K invocations |
| Realtime | 200 concurrent connections |
| Auth | 50,000 MAU |

---

## Current State Analysis

### Database Technology
- **SQLite** with 2 database files:
  - `training.db` (512KB, 159 activities)
  - `wellness.db` (192KB, 60 wellness records)

### Schema Overview (22 tables defined, ~5 actively used)

```
Core Tables:
├── activity_metrics      (159 rows) - Workout data with calculated metrics
├── fitness_metrics       (18 rows)  - Daily CTL/ATL/TSB
├── analysis_cache        (1 row)    - LLM analysis caching
├── workouts             (0 rows)    - AI-generated workouts
└── garmin_fitness_data  (varies)    - VO2max, race predictions

Strava Integration:
├── strava_credentials   - OAuth tokens (has user_id)
├── strava_preferences   - Sync settings
└── strava_activity_sync - Sync status tracking

Gamification (defined but unused):
├── achievements         - Achievement definitions
├── user_achievements    - Unlocked achievements
└── user_progress        - XP, levels, streaks
```

### Current Issues

1. **No multi-user support** - All data belongs to hardcoded `"default"` user
2. **No Garmin credential storage** - Credentials passed per-request
3. **No AI cost tracking** - Token usage not persisted
4. **N+1 query problems** - Inefficient pagination
5. **No connection pooling** - New connection per request

---

## Authentication Strategy

### Overview

The app uses a three-provider authentication model:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Authentication Architecture                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────┐                                              │
│   │   Google     │ ──── App Login (User Identity)               │
│   │   OAuth 2.0  │      • Sign in with Google                   │
│   └──────────────┘      • No password management                │
│         │               • Email verified automatically          │
│         │               • Handled by Supabase Auth              │
│         ▼                                                       │
│   ┌──────────────┐                                              │
│   │   App User   │ ──── Created on first Google sign-in        │
│   │   Account    │      • Subscription status                   │
│   └──────────────┘      • Usage tracking                        │
│         │                                                       │
│         ├─────────────────────────────────────┐                 │
│         ▼                                     ▼                 │
│   ┌──────────────┐                     ┌──────────────┐        │
│   │   Garmin     │                     │   Strava     │        │
│   │   Connect    │                     │   OAuth 2.0  │        │
│   └──────────────┘                     └──────────────┘        │
│   • Email/password                     • OAuth tokens           │
│   • Encrypted in DB                    • Already implemented    │
│   • Auto-sync daily                    • Webhook real-time      │
│   • Optional                           • Optional               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Provider Roles

| Provider | Role | Auth Method | Implementation |
|----------|------|-------------|----------------|
| **Google** | App login | OAuth 2.0 | Supabase Auth (built-in) |
| **Garmin** | Data source | Email/password | Encrypted in DB |
| **Strava** | Data source | OAuth 2.0 | ✅ Already implemented |

### User Flow

1. **First Visit**: User clicks "Sign in with Google"
2. **Google OAuth**: Supabase handles OAuth flow, creates user
3. **App Account**: User record created with free tier
4. **Connect Data Sources**: User optionally links Garmin and/or Strava
5. **Sync Data**: Activities sync automatically or on-demand

### Supabase Auth Configuration

Google OAuth is built into Supabase Auth:

```javascript
// Frontend: Sign in with Google
const { data, error } = await supabase.auth.signInWithOAuth({
  provider: 'google',
  options: {
    redirectTo: 'https://yourapp.com/auth/callback'
  }
})

// Get current user
const { data: { user } } = await supabase.auth.getUser()
```

### Database: User Auth Mapping

Supabase creates users in `auth.users` automatically. We extend with our own table:

```sql
-- Our custom user profile (extends Supabase auth.users)
CREATE TABLE public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    display_name TEXT,
    avatar_url TEXT,
    timezone TEXT DEFAULT 'UTC',

    -- Subscription (linked to Stripe)
    subscription_tier TEXT DEFAULT 'free',  -- 'free', 'pro'
    stripe_customer_id TEXT,

    -- Connected services
    garmin_connected BOOLEAN DEFAULT FALSE,
    strava_connected BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Row Level Security
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- Users can only read/update their own profile
CREATE POLICY "Users can view own profile" ON public.user_profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON public.user_profiles
    FOR UPDATE USING (auth.uid() = id);
```

---

## Stripe Payments & Subscriptions

### Overview

Monetization through subscription tiers with Stripe integration via Supabase.

### Subscription Tiers

| Feature | Free Tier | Pro Tier ($9.99/mo) |
|---------|-----------|---------------------|
| **Activity Sync** | Unlimited | Unlimited |
| **Basic Metrics** | ✅ HRSS, TRIMP, zones | ✅ All metrics |
| **AI Workout Analysis** | 5/month | Unlimited |
| **AI Training Plans** | 1 active plan | Unlimited |
| **AI Coach Chat** | 10 messages/day | Unlimited |
| **AI Workout Generation** | 3/month | Unlimited |
| **Historical Data** | 6 months | Unlimited |
| **Export Data** | ❌ | ✅ CSV/JSON |
| **Priority Sync** | ❌ | ✅ Real-time |
| **Support** | Community | Priority email |

### Stripe + Supabase Integration

Supabase has built-in Stripe integration for subscriptions:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Stripe Integration Flow                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   User clicks "Upgrade to Pro"                                  │
│         │                                                        │
│         ▼                                                        │
│   ┌──────────────┐                                              │
│   │   Stripe     │ ──── Checkout Session                        │
│   │   Checkout   │      • Hosted payment page                   │
│   └──────────────┘      • Card details handled by Stripe        │
│         │                                                        │
│         ▼                                                        │
│   ┌──────────────┐                                              │
│   │   Stripe     │ ──── customer.subscription.created           │
│   │   Webhook    │      • Sent to your backend                  │
│   └──────────────┘      • Updates user_profiles                 │
│         │                                                        │
│         ▼                                                        │
│   ┌──────────────┐                                              │
│   │   Database   │ ──── subscription_tier = 'pro'               │
│   │   Update     │      • stripe_customer_id stored             │
│   └──────────────┘      • Usage limits updated                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Database Schema: Subscriptions

```sql
-- Subscription plans definition
CREATE TABLE subscription_plans (
    id TEXT PRIMARY KEY,                    -- 'free', 'pro'
    name TEXT NOT NULL,
    description TEXT,
    price_cents INTEGER DEFAULT 0,          -- 0 for free, 999 for $9.99
    billing_period TEXT DEFAULT 'month',    -- 'month', 'year'
    stripe_price_id TEXT,                   -- Stripe Price ID

    -- Feature limits (NULL = unlimited)
    ai_analyses_per_month INTEGER,
    ai_plans_limit INTEGER,
    ai_chat_messages_per_day INTEGER,
    ai_workouts_per_month INTEGER,
    history_days INTEGER,

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default plans
INSERT INTO subscription_plans (id, name, price_cents, ai_analyses_per_month, ai_plans_limit, ai_chat_messages_per_day, ai_workouts_per_month, history_days) VALUES
    ('free', 'Free', 0, 5, 1, 10, 3, 180),
    ('pro', 'Pro', 999, NULL, NULL, NULL, NULL, NULL);  -- NULL = unlimited

-- User subscriptions
CREATE TABLE user_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Current subscription
    plan_id TEXT NOT NULL REFERENCES subscription_plans(id) DEFAULT 'free',
    status TEXT DEFAULT 'active',           -- 'active', 'canceled', 'past_due', 'trialing'

    -- Stripe references
    stripe_customer_id TEXT UNIQUE,
    stripe_subscription_id TEXT UNIQUE,

    -- Billing period
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,

    -- Trial
    trial_end TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id)
);

-- Row Level Security
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own subscription" ON user_subscriptions
    FOR SELECT USING (auth.uid() = user_id);
```

### Database Schema: Usage Tracking

```sql
-- Track feature usage per billing period
CREATE TABLE user_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Billing period (resets monthly)
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    -- Usage counters
    ai_analyses_used INTEGER DEFAULT 0,
    ai_chat_messages_used INTEGER DEFAULT 0,
    ai_workouts_generated INTEGER DEFAULT 0,
    ai_tokens_used INTEGER DEFAULT 0,

    -- Cost tracking (for internal analytics)
    ai_cost_cents INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, period_start)
);

-- Index for fast lookups
CREATE INDEX idx_user_usage_period ON user_usage(user_id, period_start DESC);

-- Row Level Security
ALTER TABLE user_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own usage" ON user_usage
    FOR SELECT USING (auth.uid() = user_id);
```

### Usage Limit Check Function

```sql
-- Function to check if user can use a feature
CREATE OR REPLACE FUNCTION check_feature_limit(
    p_user_id UUID,
    p_feature TEXT  -- 'ai_analysis', 'ai_chat', 'ai_workout'
) RETURNS BOOLEAN AS $$
DECLARE
    v_plan_id TEXT;
    v_limit INTEGER;
    v_used INTEGER;
    v_period_start DATE;
BEGIN
    -- Get user's plan
    SELECT plan_id INTO v_plan_id
    FROM user_subscriptions
    WHERE user_id = p_user_id AND status = 'active';

    IF v_plan_id IS NULL THEN
        v_plan_id := 'free';
    END IF;

    -- Get limit for this feature
    SELECT
        CASE p_feature
            WHEN 'ai_analysis' THEN ai_analyses_per_month
            WHEN 'ai_chat' THEN ai_chat_messages_per_day
            WHEN 'ai_workout' THEN ai_workouts_per_month
        END INTO v_limit
    FROM subscription_plans
    WHERE id = v_plan_id;

    -- NULL means unlimited
    IF v_limit IS NULL THEN
        RETURN TRUE;
    END IF;

    -- Get current usage
    v_period_start := date_trunc('month', CURRENT_DATE)::DATE;

    SELECT
        CASE p_feature
            WHEN 'ai_analysis' THEN ai_analyses_used
            WHEN 'ai_chat' THEN ai_chat_messages_used
            WHEN 'ai_workout' THEN ai_workouts_generated
        END INTO v_used
    FROM user_usage
    WHERE user_id = p_user_id AND period_start = v_period_start;

    IF v_used IS NULL THEN
        v_used := 0;
    END IF;

    RETURN v_used < v_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### Stripe Webhook Handler (Backend)

```python
# src/api/routes/stripe_webhook.py
from fastapi import APIRouter, Request, HTTPException
import stripe

router = APIRouter()

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(400, "Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")

    # Handle subscription events
    if event.type == "customer.subscription.created":
        await handle_subscription_created(event.data.object)
    elif event.type == "customer.subscription.updated":
        await handle_subscription_updated(event.data.object)
    elif event.type == "customer.subscription.deleted":
        await handle_subscription_deleted(event.data.object)
    elif event.type == "invoice.payment_succeeded":
        await handle_payment_succeeded(event.data.object)
    elif event.type == "invoice.payment_failed":
        await handle_payment_failed(event.data.object)

    return {"status": "ok"}

async def handle_subscription_created(subscription):
    """Update user's subscription status in database."""
    customer_id = subscription.stripe_customer_id

    # Update user_subscriptions table
    await supabase.table("user_subscriptions").update({
        "plan_id": "pro",
        "status": subscription.status,
        "stripe_subscription_id": subscription.id,
        "current_period_start": subscription.current_period_start,
        "current_period_end": subscription.current_period_end
    }).eq("stripe_customer_id", customer_id).execute()
```

### Environment Variables

```bash
# Stripe configuration
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_PRO_MONTHLY=price_...
STRIPE_PRICE_ID_PRO_YEARLY=price_...
```

### Feature Gating in Application

```python
# src/services/feature_gate.py
from enum import Enum

class Feature(Enum):
    AI_ANALYSIS = "ai_analysis"
    AI_CHAT = "ai_chat"
    AI_WORKOUT = "ai_workout"
    AI_PLAN = "ai_plan"
    DATA_EXPORT = "data_export"
    PRIORITY_SYNC = "priority_sync"

async def can_use_feature(user_id: str, feature: Feature) -> bool:
    """Check if user can use a feature based on subscription."""
    result = await supabase.rpc(
        "check_feature_limit",
        {"p_user_id": user_id, "p_feature": feature.value}
    ).execute()
    return result.data

async def increment_usage(user_id: str, feature: Feature):
    """Increment usage counter for a feature."""
    period_start = datetime.now().replace(day=1).date()

    column = f"{feature.value}s_used"

    await supabase.rpc(
        "increment_usage",
        {"p_user_id": user_id, "p_column": column}
    ).execute()

# Usage in API route
@router.post("/analyze/{workout_id}")
async def analyze_workout(
    workout_id: str,
    current_user: User = Depends(get_current_user)
):
    # Check limit
    if not await can_use_feature(current_user.id, Feature.AI_ANALYSIS):
        raise HTTPException(
            402,
            "AI analysis limit reached. Upgrade to Pro for unlimited."
        )

    # Perform analysis
    result = await analysis_service.analyze(workout_id)

    # Increment usage
    await increment_usage(current_user.id, Feature.AI_ANALYSIS)

    return result
```

### Pricing Page Data

```sql
-- Query for pricing page
SELECT
    p.id,
    p.name,
    p.price_cents,
    p.billing_period,
    p.ai_analyses_per_month,
    p.ai_plans_limit,
    p.ai_chat_messages_per_day,
    p.ai_workouts_per_month,
    CASE WHEN p.history_days IS NULL THEN 'Unlimited'
         ELSE p.history_days || ' days' END as history_access
FROM subscription_plans p
WHERE p.is_active = TRUE
ORDER BY p.price_cents;
```

---

## Multi-User Architecture

### Strategy: Shared Database with Row-Level Isolation

Add `user_id` foreign key to all user-specific tables.

### New Tables

#### 1. Users Table
```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,                    -- UUID
    email TEXT UNIQUE NOT NULL,
    email_verified INTEGER DEFAULT 0,
    password_hash TEXT,                     -- bcrypt hash (NULL for OAuth)
    display_name TEXT,
    avatar_url TEXT,
    timezone TEXT DEFAULT 'UTC',
    is_active INTEGER DEFAULT 1,
    is_admin INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_login_at TEXT
);

CREATE INDEX idx_users_email ON users(email);
```

#### 2. User Sessions Table
```sql
CREATE TABLE user_sessions (
    id TEXT PRIMARY KEY,                    -- Session token
    user_id TEXT NOT NULL,
    user_agent TEXT,
    ip_address TEXT,
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_sessions_expires ON user_sessions(expires_at);
```

#### 3. OAuth Providers Table
```sql
CREATE TABLE user_oauth_providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    provider TEXT NOT NULL,                 -- 'strava', 'garmin', 'google'
    provider_user_id TEXT NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    expires_at TEXT,
    scope TEXT,
    provider_data TEXT,                     -- JSON
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, provider)
);
```

### Tables Requiring user_id Column

| Table | Migration Priority |
|-------|-------------------|
| `activity_metrics` | High |
| `fitness_metrics` | High |
| `workouts` | High |
| `training_plans` | High |
| `workout_analyses` | High |
| `garmin_fitness_data` | High |
| `race_goals` | Medium |
| `weekly_summaries` | Medium |
| `user_achievements` | Medium |
| `user_progress` | Medium (already has it) |

### Authentication Middleware

```python
# src/api/middleware/auth.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
import jwt

security = HTTPBearer()

async def get_current_user(credentials = Depends(security)) -> CurrentUser:
    """Extract and validate user from JWT token."""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return CurrentUser(
            user_id=payload["sub"],
            email=payload["email"],
            is_admin=payload.get("is_admin", False)
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
```

---

## AI Cost Tracking System

### Overview

Track all LLM API calls with token counts, costs, and per-user rate limiting.

### Current AI Usage

| Agent | Model | Use Case |
|-------|-------|----------|
| `AnalysisAgent` | gpt-5-mini | Workout analysis |
| `ChatAgent` | gpt-5-nano/mini | Conversational coaching |
| `CoachAgent` | gpt-5-mini | Training recommendations |
| `PlanAgent` | gpt-5-mini | Training plan generation |
| `AdaptationAgent` | gpt-5-mini | Plan adjustments |

### Database Schema

#### AI Usage Logs Table
```sql
CREATE TABLE ai_usage_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT UNIQUE NOT NULL,
    user_id TEXT DEFAULT 'default',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    duration_ms INTEGER,

    -- Model info
    provider TEXT DEFAULT 'openai',
    model_id TEXT NOT NULL,
    model_type TEXT,                        -- 'fast' or 'smart'

    -- Token usage
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER GENERATED ALWAYS AS (input_tokens + output_tokens) STORED,

    -- Cost (in USD cents)
    input_cost_cents INTEGER DEFAULT 0,
    output_cost_cents INTEGER DEFAULT 0,
    total_cost_cents INTEGER GENERATED ALWAYS AS (input_cost_cents + output_cost_cents) STORED,

    -- Context
    analysis_type TEXT NOT NULL,            -- 'workout_analysis', 'chat', etc.
    entity_type TEXT,                       -- 'workout', 'plan'
    entity_id TEXT,                         -- workout_id, plan_id

    -- Status
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    is_cached INTEGER DEFAULT 0,

    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_ai_usage_user ON ai_usage_logs(user_id);
CREATE INDEX idx_ai_usage_created ON ai_usage_logs(created_at);
CREATE INDEX idx_ai_usage_type ON ai_usage_logs(analysis_type);
```

#### Model Pricing Table
```sql
CREATE TABLE ai_model_pricing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    model_id TEXT NOT NULL,
    input_price_per_million_cents INTEGER NOT NULL,
    output_price_per_million_cents INTEGER NOT NULL,
    effective_from TEXT DEFAULT CURRENT_TIMESTAMP,
    effective_until TEXT,
    UNIQUE(provider, model_id, effective_from)
);

-- Current pricing (hypothetical gpt-5 models)
INSERT INTO ai_model_pricing (provider, model_id, input_price_per_million_cents, output_price_per_million_cents)
VALUES
    ('openai', 'gpt-5-nano', 15, 60),
    ('openai', 'gpt-5-mini', 75, 300);
```

#### User Rate Limits Table
```sql
CREATE TABLE ai_user_limits (
    user_id TEXT PRIMARY KEY,
    daily_request_limit INTEGER DEFAULT 100,
    daily_token_limit INTEGER DEFAULT 500000,
    daily_cost_limit_cents INTEGER DEFAULT 500,      -- $5/day
    monthly_cost_limit_cents INTEGER DEFAULT 5000,   -- $50/month
    current_daily_requests INTEGER DEFAULT 0,
    current_daily_cost_cents INTEGER DEFAULT 0,
    current_monthly_cost_cents INTEGER DEFAULT 0,
    daily_reset_at TEXT,
    monthly_reset_at TEXT,
    is_rate_limited INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Usage Reporting Queries

```sql
-- Daily cost summary
SELECT
    date(created_at) as date,
    COUNT(*) as requests,
    SUM(total_tokens) as tokens,
    ROUND(SUM(total_cost_cents) / 100.0, 2) as cost_usd
FROM ai_usage_logs
WHERE user_id = ?
GROUP BY date(created_at)
ORDER BY date DESC;

-- Cost by analysis type
SELECT
    analysis_type,
    COUNT(*) as requests,
    ROUND(SUM(total_cost_cents) / 100.0, 2) as cost_usd
FROM ai_usage_logs
WHERE user_id = ? AND date(created_at) >= date('now', '-30 days')
GROUP BY analysis_type;
```

---

## Garmin Auto-Sync with Credential Storage

### Current State

| Aspect | Status | Issue |
|--------|--------|-------|
| Authentication | Email/password | Not stored, passed per-request |
| Token Storage | None | garth tokens saved to filesystem only |
| Sync Trigger | Manual only | No scheduled jobs |
| Multi-user | No | Single user hardcoded |

### Target Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Auto-Sync Architecture                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌─────────────────┐    ┌──────────────────┐   │
│  │  User    │───►│ Garmin Creds    │───►│ Scheduler        │   │
│  │  Setup   │    │ (Encrypted)     │    │ (APScheduler)    │   │
│  └──────────┘    └─────────────────┘    └────────┬─────────┘   │
│                                                   │              │
│                                                   ▼              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Daily Sync Job                         │   │
│  │  1. Decrypt credentials                                   │   │
│  │  2. Authenticate with Garmin                              │   │
│  │  3. Fetch new activities (since last sync)                │   │
│  │  4. Calculate metrics (HRSS, TRIMP, zones)                │   │
│  │  5. Update fitness metrics (VO2max, predictions)          │   │
│  │  6. Store sync history                                    │   │
│  │  7. Notify user (optional)                                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Database Schema

#### Garmin Credentials Table
```sql
CREATE TABLE garmin_credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL UNIQUE,

    -- Encrypted credentials (using Fernet symmetric encryption)
    encrypted_email TEXT NOT NULL,
    encrypted_password TEXT NOT NULL,
    encryption_key_id TEXT NOT NULL,        -- Reference to key rotation

    -- OAuth tokens (if using garminconnect session)
    oauth1_token TEXT,                      -- Encrypted
    oauth1_token_secret TEXT,               -- Encrypted
    session_data TEXT,                      -- Encrypted JSON (garth tokens)

    -- Metadata
    garmin_user_id TEXT,
    garmin_display_name TEXT,

    -- Status
    is_valid INTEGER DEFAULT 1,
    last_validation_at TEXT,
    validation_error TEXT,

    -- Timestamps
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_garmin_creds_user ON garmin_credentials(user_id);
```

#### Garmin Sync Configuration Table
```sql
CREATE TABLE garmin_sync_config (
    user_id TEXT PRIMARY KEY,

    -- Sync settings
    auto_sync_enabled INTEGER DEFAULT 1,
    sync_frequency TEXT DEFAULT 'daily',    -- 'hourly', 'daily', 'weekly'
    sync_time TEXT DEFAULT '06:00',         -- Preferred sync time (UTC)

    -- Data to sync
    sync_activities INTEGER DEFAULT 1,
    sync_wellness INTEGER DEFAULT 1,
    sync_fitness_metrics INTEGER DEFAULT 1,
    sync_sleep INTEGER DEFAULT 1,

    -- Lookback settings
    initial_sync_days INTEGER DEFAULT 365,  -- First sync: 1 year back
    incremental_sync_days INTEGER DEFAULT 7,-- Subsequent: 7 days back

    -- Rate limiting
    min_sync_interval_minutes INTEGER DEFAULT 60,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

#### Garmin Sync History Table
```sql
CREATE TABLE garmin_sync_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,

    -- Sync details
    sync_type TEXT NOT NULL,                -- 'manual', 'scheduled', 'webhook'
    started_at TEXT NOT NULL,
    completed_at TEXT,
    duration_seconds INTEGER,

    -- Results
    status TEXT DEFAULT 'running',          -- 'running', 'completed', 'failed', 'partial'
    activities_synced INTEGER DEFAULT 0,
    wellness_days_synced INTEGER DEFAULT 0,
    fitness_days_synced INTEGER DEFAULT 0,

    -- Date range
    sync_from_date TEXT,
    sync_to_date TEXT,

    -- Errors
    error_message TEXT,
    error_details TEXT,                     -- JSON with stack trace
    retry_count INTEGER DEFAULT 0,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_sync_history_user ON garmin_sync_history(user_id);
CREATE INDEX idx_sync_history_started ON garmin_sync_history(started_at DESC);
```

### Credential Encryption

```python
# src/services/encryption.py
from cryptography.fernet import Fernet
from typing import Optional
import os

class CredentialEncryption:
    """Secure credential encryption using Fernet (AES-128-CBC)."""

    def __init__(self):
        self._key = os.getenv("CREDENTIAL_ENCRYPTION_KEY")
        if not self._key:
            raise ValueError("CREDENTIAL_ENCRYPTION_KEY not set")
        self._fernet = Fernet(self._key.encode())

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string value."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt an encrypted value."""
        return self._fernet.decrypt(ciphertext.encode()).decode()

    @staticmethod
    def generate_key() -> str:
        """Generate a new encryption key."""
        return Fernet.generate_key().decode()
```

### Garmin Credentials Repository

```python
# src/db/repositories/garmin_repository.py
from dataclasses import dataclass
from typing import Optional
from ..encryption import CredentialEncryption

@dataclass
class GarminCredentials:
    user_id: str
    email: str                              # Decrypted
    password: str                           # Decrypted
    garmin_user_id: Optional[str] = None
    garmin_display_name: Optional[str] = None
    is_valid: bool = True

class GarminCredentialsRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.encryption = CredentialEncryption()

    def save_credentials(
        self,
        user_id: str,
        email: str,
        password: str
    ) -> GarminCredentials:
        """Save encrypted Garmin credentials."""
        encrypted_email = self.encryption.encrypt(email)
        encrypted_password = self.encryption.encrypt(password)

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO garmin_credentials
                (user_id, encrypted_email, encrypted_password, encryption_key_id)
                VALUES (?, ?, ?, 'v1')
                ON CONFLICT(user_id) DO UPDATE SET
                    encrypted_email = excluded.encrypted_email,
                    encrypted_password = excluded.encrypted_password,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, encrypted_email, encrypted_password))

        return GarminCredentials(user_id=user_id, email=email, password=password)

    def get_credentials(self, user_id: str) -> Optional[GarminCredentials]:
        """Retrieve and decrypt Garmin credentials."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM garmin_credentials WHERE user_id = ? AND is_valid = 1",
                (user_id,)
            ).fetchone()

            if not row:
                return None

            return GarminCredentials(
                user_id=row["user_id"],
                email=self.encryption.decrypt(row["encrypted_email"]),
                password=self.encryption.decrypt(row["encrypted_password"]),
                garmin_user_id=row["garmin_user_id"],
                garmin_display_name=row["garmin_display_name"],
                is_valid=bool(row["is_valid"])
            )

    def get_all_auto_sync_users(self) -> list[str]:
        """Get all users with auto-sync enabled."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT gc.user_id
                FROM garmin_credentials gc
                JOIN garmin_sync_config gsc ON gc.user_id = gsc.user_id
                WHERE gc.is_valid = 1 AND gsc.auto_sync_enabled = 1
            """).fetchall()
            return [row["user_id"] for row in rows]
```

### Scheduled Sync Service

```python
# src/services/garmin_sync_scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class GarminSyncScheduler:
    """Manages scheduled Garmin sync jobs for all users."""

    def __init__(
        self,
        garmin_repo: GarminCredentialsRepository,
        sync_service: GarminSyncService,
        training_db: TrainingDatabase
    ):
        self.garmin_repo = garmin_repo
        self.sync_service = sync_service
        self.training_db = training_db
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """Start the scheduler with daily sync job."""
        # Run daily at 6 AM UTC
        self.scheduler.add_job(
            self._run_all_syncs,
            CronTrigger(hour=6, minute=0),
            id="daily_garmin_sync",
            name="Daily Garmin Sync",
            replace_existing=True
        )

        # Also run on startup (catch up)
        self.scheduler.add_job(
            self._run_all_syncs,
            "date",
            run_date=datetime.now() + timedelta(seconds=30),
            id="startup_sync"
        )

        self.scheduler.start()
        logger.info("Garmin sync scheduler started")

    async def _run_all_syncs(self):
        """Execute sync for all users with auto-sync enabled."""
        user_ids = self.garmin_repo.get_all_auto_sync_users()
        logger.info(f"Starting scheduled sync for {len(user_ids)} users")

        for user_id in user_ids:
            try:
                await self._sync_user(user_id)
            except Exception as e:
                logger.error(f"Sync failed for user {user_id}: {e}")

    async def _sync_user(self, user_id: str):
        """Sync a single user's Garmin data."""
        credentials = self.garmin_repo.get_credentials(user_id)
        if not credentials:
            logger.warning(f"No credentials for user {user_id}")
            return

        config = self.garmin_repo.get_sync_config(user_id)

        # Determine sync date range
        last_sync = self.garmin_repo.get_last_successful_sync(user_id)
        if last_sync:
            start_date = last_sync.sync_to_date
        else:
            start_date = (datetime.now() - timedelta(days=config.initial_sync_days)).date()

        end_date = datetime.now().date()

        # Record sync start
        sync_id = self.garmin_repo.start_sync(user_id, "scheduled", start_date, end_date)

        try:
            result = await self.sync_service.sync(
                email=credentials.email,
                password=credentials.password,
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                sync_activities=config.sync_activities,
                sync_wellness=config.sync_wellness,
                sync_fitness=config.sync_fitness_metrics
            )

            self.garmin_repo.complete_sync(
                sync_id=sync_id,
                status="completed",
                activities_synced=result.activities_count,
                wellness_days=result.wellness_days,
                fitness_days=result.fitness_days
            )

        except Exception as e:
            self.garmin_repo.complete_sync(
                sync_id=sync_id,
                status="failed",
                error_message=str(e)
            )
            raise
```

### API Endpoints

```python
# src/api/routes/garmin_credentials.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/garmin", tags=["garmin"])

class SaveCredentialsRequest(BaseModel):
    email: EmailStr
    password: str

class SyncConfigRequest(BaseModel):
    auto_sync_enabled: bool = True
    sync_frequency: str = "daily"
    sync_time: str = "06:00"
    sync_activities: bool = True
    sync_wellness: bool = True
    sync_fitness_metrics: bool = True

@router.post("/credentials")
async def save_garmin_credentials(
    request: SaveCredentialsRequest,
    current_user: CurrentUser = Depends(get_current_user),
    garmin_repo: GarminCredentialsRepository = Depends(get_garmin_repo)
):
    """Save Garmin Connect credentials (encrypted)."""
    # Validate credentials by attempting login
    try:
        client = Garmin(request.email, request.password)
        client.login()
        garmin_user = client.get_full_name()
    except Exception as e:
        raise HTTPException(400, f"Invalid Garmin credentials: {e}")

    # Save encrypted credentials
    creds = garmin_repo.save_credentials(
        user_id=current_user.user_id,
        email=request.email,
        password=request.password
    )

    # Update Garmin user info
    garmin_repo.update_garmin_user(
        user_id=current_user.user_id,
        garmin_user_id=str(client.display_name),
        garmin_display_name=garmin_user
    )

    return {"status": "saved", "garmin_user": garmin_user}

@router.delete("/credentials")
async def delete_garmin_credentials(
    current_user: CurrentUser = Depends(get_current_user),
    garmin_repo: GarminCredentialsRepository = Depends(get_garmin_repo)
):
    """Delete stored Garmin credentials."""
    garmin_repo.delete_credentials(current_user.user_id)
    return {"status": "deleted"}

@router.get("/credentials/status")
async def get_credentials_status(
    current_user: CurrentUser = Depends(get_current_user),
    garmin_repo: GarminCredentialsRepository = Depends(get_garmin_repo)
):
    """Check if Garmin credentials are stored and valid."""
    creds = garmin_repo.get_credentials(current_user.user_id)
    if not creds:
        return {"connected": False}

    return {
        "connected": True,
        "garmin_user": creds.garmin_display_name,
        "is_valid": creds.is_valid,
        "last_validated": creds.last_validation_at
    }

@router.put("/sync-config")
async def update_sync_config(
    request: SyncConfigRequest,
    current_user: CurrentUser = Depends(get_current_user),
    garmin_repo: GarminCredentialsRepository = Depends(get_garmin_repo)
):
    """Update Garmin sync configuration."""
    garmin_repo.update_sync_config(
        user_id=current_user.user_id,
        **request.dict()
    )
    return {"status": "updated"}

@router.get("/sync-history")
async def get_sync_history(
    limit: int = 10,
    current_user: CurrentUser = Depends(get_current_user),
    garmin_repo: GarminCredentialsRepository = Depends(get_garmin_repo)
):
    """Get recent sync history."""
    history = garmin_repo.get_sync_history(current_user.user_id, limit)
    return {"history": history}

@router.post("/sync/trigger")
async def trigger_manual_sync(
    current_user: CurrentUser = Depends(get_current_user),
    sync_scheduler: GarminSyncScheduler = Depends(get_scheduler)
):
    """Manually trigger a Garmin sync."""
    await sync_scheduler._sync_user(current_user.user_id)
    return {"status": "sync_started"}
```

### Environment Variables

```bash
# Required for credential encryption
CREDENTIAL_ENCRYPTION_KEY="your-32-byte-base64-key"  # Generate with Fernet.generate_key()

# Optional: Configure sync behavior
GARMIN_SYNC_ENABLED=true
GARMIN_SYNC_HOUR=6                        # UTC hour for daily sync
GARMIN_SYNC_MAX_RETRIES=3
```

### Security Considerations

1. **Encryption at Rest**: Credentials encrypted with Fernet (AES-128-CBC)
2. **Key Rotation**: `encryption_key_id` supports key rotation
3. **Validation**: Credentials validated on save
4. **Audit Trail**: All syncs logged in `garmin_sync_history`
5. **Rate Limiting**: Minimum interval between syncs
6. **Session Management**: Garth tokens can be stored for session reuse

---

## Performance Optimization

### Missing Indexes to Add

```sql
-- Pagination indexes
CREATE INDEX idx_activity_metrics_date_id ON activity_metrics(date DESC, activity_id);
CREATE INDEX idx_activity_metrics_type_date ON activity_metrics(activity_type, date DESC);

-- Partial indexes
CREATE INDEX idx_activity_metrics_hrss ON activity_metrics(hrss DESC) WHERE hrss IS NOT NULL;
CREATE INDEX idx_strava_sync_pending ON strava_activity_sync(sync_status, created_at) WHERE sync_status = 'pending';

-- Covering index for list queries
CREATE INDEX idx_activity_metrics_list ON activity_metrics(date DESC, activity_id, activity_name, activity_type, duration_min, distance_km);
```

### Fix N+1 Query in Workout Listing

**Current** (inefficient):
```python
# Loads ALL activities then slices in Python!
activities = training_db.get_activities_range(start_date, end_date)
paginated = activities[offset:offset + pageSize]
```

**Fixed** (server-side pagination):
```python
def get_activities_paginated(
    self,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    activity_type: Optional[str] = None
) -> Tuple[List[ActivityMetrics], int]:
    """Get paginated activities with total count."""
    offset = (page - 1) * page_size

    with self._get_connection() as conn:
        # Count query
        total = conn.execute(
            "SELECT COUNT(*) FROM activity_metrics WHERE user_id = ?",
            (user_id,)
        ).fetchone()[0]

        # Paginated query
        rows = conn.execute("""
            SELECT * FROM activity_metrics
            WHERE user_id = ?
            ORDER BY date DESC, activity_id
            LIMIT ? OFFSET ?
        """, (user_id, page_size, offset)).fetchall()

        return [ActivityMetrics(**dict(r)) for r in rows], total
```

### Connection Pooling

```python
class SQLiteConnectionPool:
    def __init__(self, db_path: str, pool_size: int = 5):
        self.db_path = db_path
        self._pool = Queue(maxsize=pool_size)

        # Pre-populate pool
        for _ in range(pool_size):
            conn = self._create_connection()
            self._pool.put(conn)

    def _create_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row

        # Performance optimizations
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-64000")  # 64MB
        conn.execute("PRAGMA temp_store=MEMORY")

        return conn

    @contextmanager
    def get_connection(self):
        conn = self._pool.get(timeout=30)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.put(conn)
```

---

## Deployment Strategy

### Phase 1: Local Development (Current)

**SQLite** for local development - no changes needed.

```bash
# Current databases
training-analyzer/training.db    # Activities, fitness, workouts
whoop-dashboard/wellness.db      # Sleep, HRV, stress
```

### Phase 2: Production - Supabase (PostgreSQL)

**Why Supabase:**
- PostgreSQL with built-in auth, realtime, storage
- Generous free tier (500MB database)
- **Claude Code Supabase MCP** for easy management
- Row Level Security (RLS) for multi-tenancy
- Auto-generated REST/GraphQL APIs

### Claude Code Supabase MCP Integration

The Supabase MCP is configured in this project:

**Configuration** (`.mcp.json`):
```json
{
  "mcpServers": {
    "supabase": {
      "type": "http",
      "url": "https://mcp.supabase.com/mcp"
    }
  }
}
```

**Available MCP Tools:**
- Create/manage tables and schemas
- Generate and apply migrations
- Execute SQL queries
- Generate TypeScript types
- List projects and manage settings
- Deploy Edge Functions
- View logs and debug

**First Time Setup:**
1. When you use a Supabase MCP tool, Claude Code opens browser for auth
2. Log in to your Supabase account
3. Authorize Claude Code access
4. MCP tools become available

**Project Scoping (Recommended for Safety):**
```json
{
  "mcpServers": {
    "supabase": {
      "type": "http",
      "url": "https://mcp.supabase.com/mcp?project_ref=YOUR_PROJECT_ID"
    }
  }
}
```

### Supabase Setup Steps

```bash
# 1. Create Supabase project at https://supabase.com
#    - Choose region closest to you
#    - Note Project URL and anon/service keys

# 2. Use Claude Code to create tables:
#    Ask: "Create the users table in Supabase"
#    Claude will use MCP to execute the migration

# 3. Set environment variables
```

### Environment Configuration

```bash
# .env.production
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIs...  # For backend only

CREDENTIAL_ENCRYPTION_KEY=your-fernet-key

OPENAI_API_KEY=sk-...
```

### SQLite to PostgreSQL Migration Notes

**Syntax Changes Required:**
| SQLite | PostgreSQL |
|--------|------------|
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `SERIAL PRIMARY KEY` |
| `TEXT` | `TEXT` or `VARCHAR(n)` |
| `REAL` | `DOUBLE PRECISION` |
| `INTEGER` (boolean) | `BOOLEAN` |
| `CURRENT_TIMESTAMP` | `NOW()` or `CURRENT_TIMESTAMP` |

**Connection Code Change:**
```python
# SQLite (current)
import sqlite3
conn = sqlite3.connect("training.db")

# PostgreSQL (future)
from supabase import create_client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Or with psycopg2 for direct access
import psycopg2
conn = psycopg2.connect(DATABASE_URL)
```

### Supabase Free Tier Limits

| Resource | Limit | Notes |
|----------|-------|-------|
| Database | 500 MB | Enough for ~5,000 activities |
| Bandwidth | 5 GB/month | API + realtime |
| Storage | 1 GB | For files/images |
| Edge Functions | 500K/month | Serverless compute |
| Auth Users | 50,000 MAU | Built-in auth |
| Realtime | 200 connections | Live updates |

### Deployment Targets

| Component | Platform | Cost |
|-----------|----------|------|
| Frontend | Vercel | Free |
| Backend | Railway / Vercel | Free-$5/mo |
| Database | Supabase | **Free** |
| **Total** | | **$0-5/mo** |

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [ ] Create `users` table and auth middleware
- [ ] Add `user_id` to all user-specific tables
- [ ] Migrate existing data to default user
- [ ] Update all repositories with user_id parameter

### Phase 2: Garmin Auto-Sync (Week 2)
- [ ] Create `garmin_credentials` table with encryption
- [ ] Create `garmin_sync_config` table
- [ ] Create `garmin_sync_history` table
- [ ] Implement `GarminCredentialsRepository`
- [ ] Implement `GarminSyncScheduler` with APScheduler
- [ ] Create credential management API endpoints
- [ ] Add frontend UI for credential setup

### Phase 3: AI Cost Tracking (Week 2-3)
- [ ] Create `ai_usage_logs` table
- [ ] Create `ai_model_pricing` table
- [ ] Create `ai_user_limits` table
- [ ] Modify `LLMClient` to log usage
- [ ] Add rate limiting middleware
- [ ] Create usage dashboard API

### Phase 4: Performance (Week 3)
- [ ] Add missing database indexes
- [ ] Implement connection pooling
- [ ] Fix N+1 query in workout listing
- [ ] Add server-side pagination

### Phase 5: Deployment (Week 4)
- [ ] Set up Turso databases
- [ ] Configure environment variables
- [ ] Migrate data to cloud
- [ ] Set up monitoring
- [ ] Deploy backend to Railway
- [ ] Deploy frontend to Vercel

---

## Files to Create/Modify

### New Files
```
src/db/repositories/garmin_repository.py
src/db/repositories/ai_usage_repository.py
src/db/repositories/user_repository.py
src/services/encryption.py
src/services/garmin_sync_scheduler.py
src/api/routes/garmin_credentials.py
src/api/routes/auth.py
src/api/routes/usage.py
src/api/middleware/auth.py
```

### Modified Files
```
src/db/schema.py                    # Add all new tables
src/db/database.py                  # Add connection pooling, user_id params
src/db/repositories/workout_repository.py
src/db/repositories/plan_repository.py
src/db/repositories/strava_repository.py
src/api/routes/workouts.py          # Add auth dependency
src/api/routes/analysis.py          # Add auth dependency
src/llm/providers.py                # Add usage logging
src/config.py                       # Add new config options
src/main.py                         # Initialize scheduler
```

---

## Security Checklist

- [ ] Credentials encrypted at rest (Fernet)
- [ ] JWT tokens with expiration
- [ ] HTTPS only in production
- [ ] Rate limiting on all endpoints
- [ ] Audit logging for sensitive operations
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (parameterized queries)
- [ ] CORS configuration for frontend only
- [ ] Environment variables for all secrets
- [ ] No secrets in git repository
