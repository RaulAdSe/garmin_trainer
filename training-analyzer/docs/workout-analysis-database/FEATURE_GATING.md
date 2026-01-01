# Feature Gating

This document describes the subscription-based feature gating system for controlling access to AI features based on user subscription tier.

## Overview

The feature gate service:

- **Enforces Limits**: Restricts feature usage based on subscription tier
- **Tracks Usage**: Counts daily and monthly feature usage per user
- **Auto-Resets**: Resets counters at the start of each day/month
- **Returns Errors**: HTTP 402 (Payment Required) when limits are reached

## Features

The system tracks these AI features:

| Feature | Enum Value | Description |
|---------|------------|-------------|
| AI Analysis | `ai_analysis` | Workout analysis requests |
| AI Chat | `ai_chat` | AI coaching chat messages |
| AI Workout | `ai_workout` | AI-generated workouts |
| AI Plan | `ai_plan` | AI training plan generation |
| Data Export | `data_export` | Export data (Pro only) |
| Priority Sync | `priority_sync` | Priority Garmin sync (Pro only) |

## Subscription Limits

### Free Tier

| Feature | Daily Limit | Monthly Limit |
|---------|-------------|---------------|
| AI Analysis | - | 5 |
| AI Chat | 10 | - |
| AI Workout | - | 3 |
| AI Plan | - | 1 |
| Data Export | - | 0 (disabled) |
| Priority Sync | - | 0 (disabled) |

### Pro Tier

All features are **unlimited** for Pro subscribers.

### Enterprise Tier

All features are **unlimited** for Enterprise subscribers.

## Usage

### Basic Usage Check

```python
from training_analyzer.services.feature_gate import (
    can_use_feature,
    increment_usage,
    Feature,
)

# Check if user can use a feature
if can_use_feature(user_id, Feature.AI_ANALYSIS, subscription_tier="free"):
    # Feature is available
    do_analysis()
    increment_usage(user_id, Feature.AI_ANALYSIS)
else:
    # Limit reached
    raise HTTPException(402, "Monthly limit reached for AI analyses")
```

### Check and Increment (Recommended)

```python
from training_analyzer.services.feature_gate import check_and_increment, Feature

# This automatically:
# 1. Checks if feature is available
# 2. Raises HTTP 402 if limit reached
# 3. Increments usage counter if available
check_and_increment(user_id, Feature.AI_ANALYSIS, subscription_tier)

# Now safe to use the feature
result = perform_ai_analysis()
```

### Get Usage Summary

```python
from training_analyzer.services.feature_gate import get_usage_summary

summary = get_usage_summary(user_id, subscription_tier="free")

# Returns dict of feature -> UsageSummary
for feature, usage in summary.items():
    print(f"{feature}:")
    print(f"  Current: {usage.current_usage}")
    print(f"  Limit: {usage.limit}")
    print(f"  Remaining: {usage.remaining}")
    print(f"  Limited: {usage.is_limited}")
    print(f"  Period: {usage.period}")  # "daily", "monthly", or "unlimited"
```

### Get Feature Availability

```python
from training_analyzer.services.feature_gate import get_feature_gate_service

service = get_feature_gate_service()
availability = service.get_feature_availability(subscription_tier="free")

# Returns dict of feature -> availability info
# {
#   "ai_analysis": {
#     "available": True,
#     "unlimited": False,
#     "monthly_limit": 5,
#     "daily_limit": None
#   },
#   "data_export": {
#     "available": False,
#     "unlimited": False,
#     "monthly_limit": 0,
#     "daily_limit": None
#   },
#   ...
# }
```

## API Integration

### FastAPI Middleware Example

```python
from fastapi import Depends, HTTPException
from training_analyzer.services.feature_gate import check_and_increment, Feature

async def require_ai_analysis(user: dict = Depends(get_current_user)):
    """Dependency that checks AI analysis quota."""
    check_and_increment(
        user["user_id"],
        Feature.AI_ANALYSIS,
        user["tier"]
    )
    return user

@app.post("/api/analyze")
async def analyze_workout(
    workout_id: str,
    user: dict = Depends(require_ai_analysis)  # Checks quota
):
    # Quota already checked and incremented
    return perform_analysis(workout_id)
```

### Error Response

When a limit is reached, `check_and_increment` raises:

```python
HTTPException(
    status_code=402,  # Payment Required
    detail="Monthly limit reached for AI analyses. Upgrade to Pro for unlimited access."
)
```

For disabled features (like Data Export on Free):

```python
HTTPException(
    status_code=402,
    detail="Data export is not available on the Free plan. Upgrade to Pro to unlock this feature."
)
```

## Counter Reset Behavior

### Daily Counters

- Reset at midnight UTC
- Used for: `AI_CHAT` messages

### Monthly Counters

- Reset on the 1st of each month at midnight UTC
- Used for: `AI_ANALYSIS`, `AI_WORKOUT`, `AI_PLAN`

The service automatically checks and resets counters when retrieving usage.

## Data Structures

### Feature Enum

```python
class Feature(Enum):
    AI_ANALYSIS = "ai_analysis"
    AI_CHAT = "ai_chat"
    AI_WORKOUT = "ai_workout"
    AI_PLAN = "ai_plan"
    DATA_EXPORT = "data_export"
    PRIORITY_SYNC = "priority_sync"
```

### FeatureLimit

```python
@dataclass
class FeatureLimit:
    monthly_limit: Optional[int]  # None = unlimited
    daily_limit: Optional[int]    # None = no daily limit
```

### UsageSummary

```python
@dataclass
class UsageSummary:
    feature: Feature
    current_usage: int
    limit: Optional[int]          # None if unlimited
    period: str                   # "daily", "monthly", or "unlimited"
    reset_at: datetime            # When counter resets
    remaining: Optional[int]      # None if unlimited
    is_limited: bool              # True if at/over limit
```

## Configuration

Subscription limits are defined in code:

```python
# src/services/feature_gate.py

SUBSCRIPTION_LIMITS = {
    "free": {
        Feature.AI_ANALYSIS: FeatureLimit(monthly_limit=5, daily_limit=None),
        Feature.AI_CHAT: FeatureLimit(monthly_limit=None, daily_limit=10),
        Feature.AI_WORKOUT: FeatureLimit(monthly_limit=3, daily_limit=None),
        Feature.AI_PLAN: FeatureLimit(monthly_limit=1, daily_limit=None),
        Feature.DATA_EXPORT: FeatureLimit(monthly_limit=0, daily_limit=None),
        Feature.PRIORITY_SYNC: FeatureLimit(monthly_limit=0, daily_limit=None),
    },
    "pro": {
        Feature.AI_ANALYSIS: FeatureLimit(monthly_limit=None, daily_limit=None),
        Feature.AI_CHAT: FeatureLimit(monthly_limit=None, daily_limit=None),
        # ... all unlimited
    },
    "enterprise": {
        # ... all unlimited
    },
}
```

## Testing

The feature gate service has 43 tests covering:

- Feature enum definitions
- Subscription limits (free, pro, enterprise)
- Usage checking (under/at/over limits)
- Daily and monthly limit enforcement
- Disabled feature handling
- Counter reset behavior
- Usage summary generation
- Check and increment pattern

Run tests:
```bash
python3 -m pytest tests/test_feature_gate.py -v
```

## Related Documentation

- [MULTI_USER_ARCHITECTURE.md](./MULTI_USER_ARCHITECTURE.md) - System overview
- [AUTHENTICATION.md](./AUTHENTICATION.md) - JWT authentication
- [AI_USAGE_TRACKING.md](./AI_USAGE_TRACKING.md) - Detailed usage logging
- [REPOSITORY_LAYER.md](./REPOSITORY_LAYER.md) - Subscription repository
