# AI Quota System

This document describes the database-backed AI usage quota system that enforces subscription-based limits on AI features.

## Overview

The quota system:

- **Tracks Actual Usage**: Queries `ai_usage_logs` table for real usage counts
- **Enforces Limits**: Blocks requests when quota is exceeded (HTTP 402)
- **Per-Subscription**: Different limits for free, pro, and enterprise tiers
- **Auto-Resets**: Daily quotas reset at midnight UTC, monthly on the 1st

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      API Request                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              require_quota("workout_analysis")               │
│                   FastAPI Dependency                         │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────────┐
│    QUOTA_LIMITS         │     │   ai_usage_logs table       │
│   (subscription tier)   │     │   get_usage_count()         │
└─────────────────────────┘     └─────────────────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              ▼
                     ┌────────────────┐
                     │  used < limit? │
                     └────────────────┘
                        │         │
                      Yes         No
                        │         │
                        ▼         ▼
               ┌──────────┐   ┌──────────────┐
               │ Continue │   │  HTTP 402    │
               │ Request  │   │ Quota Error  │
               └──────────┘   └──────────────┘
```

## Quota Limits

### Free Tier

| Feature | Limit | Period |
|---------|-------|--------|
| Workout Analysis | 5 | Monthly |
| Chat | 10 | Daily |
| Plan Generation | 0 (disabled) | - |

### Pro Tier

All features are **unlimited**.

### Enterprise Tier

All features are **unlimited**.

## Files

| File | Purpose |
|------|---------|
| `src/api/quota.py` | Quota limits configuration |
| `src/api/middleware/quota.py` | Quota enforcement dependency |
| `src/db/repositories/ai_usage_repository.py` | `get_usage_count()` method |

## Usage

### Route Protection

Use `require_quota()` as a FastAPI dependency to protect AI endpoints:

```python
from src.api.middleware.quota import require_quota

@router.post("/workout/{workout_id}")
async def analyze_workout(
    workout_id: str,
    current_user: CurrentUser = Depends(require_quota("workout_analysis")),
):
    # Quota already checked - user has remaining quota
    result = perform_analysis(workout_id)
    return result
```

### Quota Status Endpoint

Users can check their quota status via:

```
GET /api/usage/quota
```

Response:
```json
{
  "subscription_tier": "free",
  "quotas": [
    {
      "analysis_type": "workout_analysis",
      "period": "monthly",
      "limit": 5,
      "used": 3,
      "remaining": 2,
      "is_exceeded": false
    },
    {
      "analysis_type": "chat",
      "period": "daily",
      "limit": 10,
      "used": 2,
      "remaining": 8,
      "is_exceeded": false
    },
    {
      "analysis_type": "plan",
      "period": "monthly",
      "limit": 0,
      "used": 0,
      "remaining": 0,
      "is_exceeded": false
    }
  ]
}
```

## Error Responses

### Quota Exceeded (HTTP 402)

When a user exceeds their quota:

```json
{
  "error": "quota_exceeded",
  "message": "You have reached your monthly limit of 5 workout analysis requests. Upgrade to Pro for unlimited access.",
  "analysis_type": "workout_analysis",
  "period": "monthly",
  "limit": 5,
  "used": 5,
  "upgrade_url": "/settings/billing"
}
```

### Feature Disabled (HTTP 402)

When a feature is not available on the user's tier:

```json
{
  "error": "feature_unavailable",
  "message": "Plan is not available on the free plan. Upgrade to Pro to access this feature.",
  "upgrade_url": "/settings/billing"
}
```

## Configuration

Quota limits are defined in `src/api/quota.py`:

```python
from src.api.quota import QuotaLimit, QuotaPeriod

QUOTA_LIMITS = {
    "free": {
        "workout_analysis": QuotaLimit(limit=5, period=QuotaPeriod.MONTHLY),
        "chat": QuotaLimit(limit=10, period=QuotaPeriod.DAILY),
        "plan": QuotaLimit(limit=0, period=QuotaPeriod.MONTHLY),  # Disabled
    },
    "pro": {
        "workout_analysis": QuotaLimit(limit=-1, period=QuotaPeriod.MONTHLY),  # Unlimited
        "chat": QuotaLimit(limit=-1, period=QuotaPeriod.DAILY),
        "plan": QuotaLimit(limit=-1, period=QuotaPeriod.MONTHLY),
    },
    "enterprise": {
        # Same as pro - all unlimited
    },
}
```

### Limit Values

- `-1`: Unlimited (no quota enforcement)
- `0`: Feature disabled for this tier
- `>0`: Maximum requests per period

## Database Query

The quota system uses `get_usage_count()` in `AIUsageRepository`:

```python
def get_usage_count(
    self,
    user_id: str,
    analysis_type: str,
    period_start: date,
    period_end: date,
) -> int:
    """Count completed AI requests for quota enforcement."""

    # SQL query against ai_usage_logs table
    SELECT COUNT(*) FROM ai_usage_logs
    WHERE user_id = ?
      AND analysis_type = ?
      AND date(created_at) >= ?
      AND date(created_at) <= ?
      AND status = 'completed'
```

This queries actual usage from the `ai_usage_logs` table, ensuring accurate quota tracking.

## Period Reset

### Daily Quotas (e.g., Chat)

- Period: Current day (midnight to midnight UTC)
- Reset: Automatically at midnight UTC
- Query range: `today` to `today`

### Monthly Quotas (e.g., Analysis)

- Period: 1st of month to current day
- Reset: Automatically on 1st of each month
- Query range: `first_of_month` to `today`

## Internal Endpoints

The batch analysis endpoint has been removed from the public API:

```python
# NOT exposed via router - internal use only
async def batch_analyze_internal(
    request: BatchAnalysisRequest,
    user_id: str,
    coach_service,
    training_db,
):
    """For background jobs and admin tasks."""
```

## Testing

Test the quota system:

```bash
# Test quota check
curl -X POST /api/analysis/workout/123 \
  -H "Authorization: Bearer <token>"

# Check quota status
curl /api/usage/quota \
  -H "Authorization: Bearer <token>"
```

## Related Documentation

- [AI_USAGE_TRACKING.md](./AI_USAGE_TRACKING.md) - How usage is logged
- [FEATURE_GATING.md](./FEATURE_GATING.md) - Legacy in-memory feature gate
- [AUTHENTICATION.md](./AUTHENTICATION.md) - JWT and subscription tiers
- [DEPLOYMENT_GAPS.md](./DEPLOYMENT_GAPS.md) - Security implementation status
