# AI Usage Tracking

This document describes the AI usage tracking system for monitoring API costs and enforcing rate limits.

## Overview

The AI usage tracking system provides:

- **Request Logging**: Track every AI API call with tokens and costs
- **Cost Calculation**: Automatic cost calculation from model pricing
- **Usage Summaries**: Aggregated usage statistics per user
- **Rate Limiting**: Enforce daily and monthly usage limits
- **Usage History**: Historical usage data for billing and analytics

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      AI Usage Tracking Flow                              │
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │  AI Service  │───▶│  Feature     │───▶│  AI Usage    │              │
│  │  (Analysis)  │    │    Gate      │    │  Repository  │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│         │                                       │                        │
│         │                                       ▼                        │
│         │                              ┌──────────────┐                 │
│         │                              │ ai_usage_logs │                 │
│         │                              │    table     │                 │
│         │                              └──────────────┘                 │
│         │                                       │                        │
│         ▼                                       ▼                        │
│  ┌──────────────┐                      ┌──────────────┐                 │
│  │   OpenAI     │                      │ Model Pricing │                 │
│  │     API      │                      │    Table      │                 │
│  └──────────────┘                      └──────────────┘                 │
└─────────────────────────────────────────────────────────────────────────┘
```

## Logging AI Requests

### Single-Call Pattern (Recommended)

Log the complete request after it finishes:

```python
from training_analyzer.db.repositories import get_ai_usage_repository
import uuid

repo = get_ai_usage_repository()

# After AI request completes
log = repo.log_usage(
    request_id=str(uuid.uuid4()),
    user_id="usr_abc123",
    model_id="gpt-4o-mini",
    input_tokens=1500,
    output_tokens=750,
    total_cost_cents=0,  # Auto-calculated from pricing table
    analysis_type="workout_analysis",
    duration_ms=2500,
    model_type="fast",           # "fast" or "smart"
    entity_type="workout",       # What was analyzed
    entity_id="workout_123"      # ID of analyzed entity
)

print(f"Cost: ${log.total_cost_cents / 100:.4f}")
```

### Async Pattern (For Long Requests)

Start logging before the request, complete after:

```python
# Before the request
request_id = str(uuid.uuid4())
log = repo.log_request(
    request_id=request_id,
    user_id="usr_abc123",
    model_id="gpt-4o",
    analysis_type="training_plan",
    entity_type="race_goal",
    entity_id="goal_456"
)
# log.status == "pending"

# Make the AI request
try:
    response = await openai_client.chat.completions.create(...)

    # Complete with success
    repo.update_request(
        request_id=request_id,
        status="completed",
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens
    )

except Exception as e:
    # Complete with failure
    repo.update_request(
        request_id=request_id,
        status="failed",
        error_message=str(e)
    )
```

## Model Pricing

Default pricing is stored in the `ai_model_pricing` table:

| Provider | Model | Input (per 1M tokens) | Output (per 1M tokens) |
|----------|-------|----------------------|------------------------|
| openai | gpt-4o-mini | $0.15 (15¢) | $0.60 (60¢) |
| openai | gpt-4o | $2.50 (250¢) | $10.00 (1000¢) |

Cost is automatically calculated when logging:

```python
# For 1M input + 1M output tokens with gpt-4o-mini:
# Input cost:  $0.15
# Output cost: $0.60
# Total cost:  $0.75

log = repo.log_usage(
    model_id="gpt-4o-mini",
    input_tokens=1_000_000,
    output_tokens=1_000_000,
    total_cost_cents=0,  # Auto-calculated to 75
    ...
)
print(log.total_cost_cents)  # 75
```

## Usage Summaries

Get aggregated usage data:

```python
# Get current month's summary
summary = repo.get_usage_summary(user_id)

print(f"Total Requests: {summary.total_requests}")
print(f"Total Tokens: {summary.total_tokens}")
print(f"Total Cost: ${summary.total_cost_cents / 100:.2f}")
print(f"Period: {summary.period_start} to {summary.period_end}")

# By analysis type
for analysis_type, count in summary.by_analysis_type.items():
    print(f"  {analysis_type}: {count} requests")

# By model
for model, stats in summary.by_model.items():
    print(f"  {model}: {stats['requests']} requests, ${stats['cost'] / 100:.2f}")
```

## Usage History

Get historical usage data:

```python
# Daily breakdown
daily = repo.get_usage_by_date_range(
    user_id,
    start_date=date(2024, 1, 1),
    end_date=date.today()
)
for day in daily:
    print(f"{day['date']}: {day['requests']} requests, ${day['cost_usd']:.2f}")

# By analysis type
by_type = repo.get_usage_by_analysis_type(user_id, days=30)
for entry in by_type:
    print(f"{entry['analysis_type']}: {entry['requests']} requests")

# With different granularities
history = repo.get_usage_history(user_id, days=30, granularity="day")
history = repo.get_usage_history(user_id, days=90, granularity="week")
history = repo.get_usage_history(user_id, days=365, granularity="month")

# Get total cost
total_cost = repo.get_total_cost(user_id)  # Returns dollars
print(f"Total spent: ${total_cost:.2f}")
```

## Rate Limiting

Check if user has exceeded limits:

```python
limits = repo.get_usage_limits(
    user_id,
    daily_request_limit=100,
    daily_cost_limit_cents=500,    # $5/day
    monthly_cost_limit_cents=5000  # $50/month
)

if limits.is_rate_limited:
    if limits.current_daily_requests >= limits.daily_request_limit:
        raise HTTPException(429, "Daily request limit exceeded")
    if limits.current_daily_cost_cents >= limits.daily_cost_limit_cents:
        raise HTTPException(429, "Daily cost limit exceeded")
    if limits.current_monthly_cost_cents >= limits.monthly_cost_limit_cents:
        raise HTTPException(429, "Monthly cost limit exceeded")

# Can proceed with request
```

### Default Limits (from `.env`)

```bash
AI_DAILY_REQUEST_LIMIT=100
AI_DAILY_TOKEN_LIMIT=500000
AI_DAILY_COST_LIMIT_CENTS=500      # $5
AI_MONTHLY_COST_LIMIT_CENTS=5000   # $50
```

## Recent Logs

Get recent requests for a user:

```python
logs = repo.get_recent_logs(user_id, limit=20)

for log in logs:
    print(f"{log.created_at}: {log.analysis_type}")
    print(f"  Model: {log.model_id}")
    print(f"  Tokens: {log.total_tokens}")
    print(f"  Cost: ${log.total_cost_cents / 100:.4f}")
    print(f"  Status: {log.status}")
    if log.error_message:
        print(f"  Error: {log.error_message}")
```

## Data Structures

### AIUsageLog

```python
@dataclass
class AIUsageLog:
    id: Optional[int] = None
    request_id: Optional[str] = None
    user_id: str = "default"
    provider: str = "openai"
    model_id: Optional[str] = None
    model_type: Optional[str] = None     # "fast" or "smart"
    input_tokens: int = 0
    output_tokens: int = 0
    input_cost_cents: float = 0.0
    output_cost_cents: float = 0.0
    total_cost_cents: float = 0.0
    analysis_type: Optional[str] = None  # workout_analysis, chat, plan, etc.
    entity_type: Optional[str] = None    # workout, race_goal, etc.
    entity_id: Optional[str] = None
    duration_ms: Optional[int] = None
    status: str = "completed"            # pending, completed, failed
    error_message: Optional[str] = None
    is_cached: bool = False
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
```

### UsageSummary

```python
@dataclass
class UsageSummary:
    user_id: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost_cents: float = 0.0
    by_analysis_type: Dict[str, int] = field(default_factory=dict)
    by_model: Dict[str, Dict] = field(default_factory=dict)
```

### UsageLimits

```python
@dataclass
class UsageLimits:
    user_id: str
    daily_request_limit: int = 100
    daily_token_limit: int = 500000
    daily_cost_limit_cents: int = 500
    monthly_cost_limit_cents: int = 5000
    current_daily_requests: int = 0
    current_daily_tokens: int = 0
    current_daily_cost_cents: float = 0.0
    current_monthly_cost_cents: float = 0.0
    is_rate_limited: bool = False
```

## Database Tables

### ai_usage_logs

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Auto-increment ID |
| `request_id` | TEXT | Unique request identifier |
| `user_id` | TEXT | User ID |
| `provider` | TEXT | AI provider (openai) |
| `model_id` | TEXT | Model name |
| `model_type` | TEXT | fast/smart |
| `input_tokens` | INTEGER | Prompt tokens |
| `output_tokens` | INTEGER | Completion tokens |
| `input_cost_cents` | REAL | Input cost in cents |
| `output_cost_cents` | REAL | Output cost in cents |
| `total_cost_cents` | REAL | Total cost in cents |
| `analysis_type` | TEXT | Type of analysis |
| `entity_type` | TEXT | Type of entity analyzed |
| `entity_id` | TEXT | ID of entity analyzed |
| `duration_ms` | INTEGER | Request duration |
| `status` | TEXT | pending/completed/failed |
| `error_message` | TEXT | Error if failed |
| `is_cached` | INTEGER | Was response cached |
| `created_at` | TEXT | Request start time |
| `completed_at` | TEXT | Request end time |

### ai_model_pricing

| Column | Type | Description |
|--------|------|-------------|
| `provider` | TEXT | AI provider |
| `model_id` | TEXT | Model name |
| `input_cost_per_million` | REAL | Input cost per 1M tokens (cents) |
| `output_cost_per_million` | REAL | Output cost per 1M tokens (cents) |
| `is_active` | INTEGER | Is model active |
| `created_at` | TEXT | When added |

## Analysis Types

Standard analysis types used in the system:

| Type | Description |
|------|-------------|
| `workout_analysis` | Analyze a single workout |
| `weekly_analysis` | Weekly training summary |
| `chat` | AI coaching chat message |
| `training_plan` | Generate training plan |
| `race_prediction` | Predict race performance |
| `workout_generation` | Generate workout suggestions |

## Integration Example

Complete example in an API endpoint:

```python
from fastapi import APIRouter, Depends, HTTPException
from training_analyzer.services.feature_gate import check_and_increment, Feature
from training_analyzer.db.repositories import get_ai_usage_repository
import uuid

router = APIRouter()

@router.post("/api/analyze/{workout_id}")
async def analyze_workout(
    workout_id: str,
    user: dict = Depends(get_current_user)
):
    # 1. Check feature quota
    check_and_increment(user["user_id"], Feature.AI_ANALYSIS, user["tier"])

    repo = get_ai_usage_repository()
    request_id = str(uuid.uuid4())

    # 2. Start logging
    repo.log_request(
        request_id=request_id,
        user_id=user["user_id"],
        model_id="gpt-4o-mini",
        analysis_type="workout_analysis",
        entity_type="workout",
        entity_id=workout_id
    )

    try:
        # 3. Make AI request
        start = time.time()
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[...],
        )
        duration_ms = int((time.time() - start) * 1000)

        # 4. Complete logging
        repo.update_request(
            request_id=request_id,
            status="completed",
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            duration_ms=duration_ms
        )

        return {"analysis": response.choices[0].message.content}

    except Exception as e:
        # 5. Log failure
        repo.update_request(
            request_id=request_id,
            status="failed",
            error_message=str(e)
        )
        raise HTTPException(500, f"Analysis failed: {e}")
```

## Testing

The AI usage repository has 34 tests covering:

- Request logging (async and sync patterns)
- Cost calculation from pricing table
- Usage summaries and aggregations
- Usage history queries
- Rate limit checking
- Recent log retrieval

Run tests:
```bash
python3 -m pytest tests/test_ai_usage_repository.py -v
```

## Related Documentation

- [MULTI_USER_ARCHITECTURE.md](./MULTI_USER_ARCHITECTURE.md) - System overview
- [FEATURE_GATING.md](./FEATURE_GATING.md) - Subscription limits
- [REPOSITORY_LAYER.md](./REPOSITORY_LAYER.md) - Repository documentation
