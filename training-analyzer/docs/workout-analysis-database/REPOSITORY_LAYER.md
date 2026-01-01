# Repository Layer

This document describes the repository layer implementation for the Training Analyzer multi-user database.

## Overview

The repository layer provides a clean abstraction over database operations, following the Repository Pattern. Each repository handles CRUD operations for a specific domain entity.

## Base Repository

All repositories extend `BaseRepository` which provides:

```python
class BaseRepository:
    """Base class for all repositories."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or get_default_db_path())

    @contextmanager
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
```

## Repositories

### UserRepository

**File**: `src/db/repositories/user_repository.py`

Handles user account management.

```python
from training_analyzer.db.repositories import get_user_repository

repo = get_user_repository()

# Create user
user = repo.create_user(
    user_id="usr_abc123",
    email="athlete@example.com",
    password_hash="$2b$12$...",  # bcrypt hash
    display_name="John Doe",
    timezone="America/New_York"
)

# Get user by ID or email
user = repo.get_by_id("usr_abc123")
user = repo.get_by_email("athlete@example.com")

# Update user
user = repo.update(user_id, display_name="Jane Doe", timezone="UTC")

# Track login
repo.update_last_login(user_id)

# List users with pagination
users = repo.get_all(limit=20, offset=0, active_only=True)
count = repo.count(active_only=True)

# Delete user
repo.delete(user_id)
```

**User Model**:
```python
@dataclass
class User:
    id: str
    email: str
    email_verified: bool = False
    password_hash: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: str = "UTC"
    is_active: bool = True
    is_admin: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
```

---

### SubscriptionRepository

**File**: `src/db/repositories/subscription_repository.py`

Manages subscription plans, user subscriptions, and usage tracking.

```python
from training_analyzer.db.repositories import get_subscription_repository

repo = get_subscription_repository()

# Get subscription plans
free_plan = repo.get_plan("free")
pro_plan = repo.get_plan("pro")
all_plans = repo.get_all_plans(active_only=True)

# Create user subscription
subscription = repo.create_subscription(
    subscription_id="sub_123",
    user_id="usr_abc123",
    plan_id="free",
    stripe_customer_id="cus_xyz"  # Optional
)

# Get user's subscription
subscription = repo.get_user_subscription(user_id)

# Upgrade/downgrade plan
repo.update_subscription(user_id, plan_id="pro")

# Track usage
usage = repo.increment_usage(
    user_id,
    feature="ai_analyses",  # ai_analyses, ai_chat_messages, ai_workouts
    amount=1,
    tokens=1500,
    cost_cents=2
)

# Check if feature available
can_use = repo.can_use_feature(user_id, "ai_analyses")

# Get usage summary
usage = repo.get_user_usage(user_id)

# Reset usage (for new billing period)
repo.reset_usage(user_id)
```

**Subscription Plans** (default):

| Plan | Price | AI Analyses | AI Chat | AI Workouts | History |
|------|-------|-------------|---------|-------------|---------|
| Free | $0 | 5/month | 10/day | 3/month | 180 days |
| Pro | $9.99 | Unlimited | Unlimited | Unlimited | Unlimited |

---

### GarminCredentialsRepository

**File**: `src/db/repositories/garmin_credentials_repository.py`

Manages encrypted Garmin credentials, sync configuration, and sync history.

```python
from training_analyzer.db.repositories import get_garmin_credentials_repository

repo = get_garmin_credentials_repository()

# Save encrypted credentials
creds = repo.save_credentials(
    user_id="usr_abc123",
    encrypted_email="gAAAAB...",  # Fernet encrypted
    encrypted_password="gAAAAB...",
    encryption_key_id="v1",
    garmin_user_id="garmin_12345",
    garmin_display_name="JohnDoe"
)

# Get credentials
creds = repo.get_credentials(user_id)

# Update validation status
repo.update_validation_status(
    user_id,
    is_valid=True,
    validation_error=None
)

# Manage sync configuration
config = repo.update_sync_config(
    user_id,
    auto_sync_enabled=True,
    sync_frequency="daily",  # daily, hourly, weekly
    sync_time="06:00",
    sync_activities=True,
    sync_wellness=True
)

# Track sync history
sync_id = repo.start_sync(
    user_id,
    sync_type="scheduled",  # manual, scheduled, initial
    sync_from_date=date(2024, 1, 1),
    sync_to_date=date.today()
)

repo.complete_sync(
    sync_id,
    status="completed",  # completed, failed, partial
    activities_synced=15,
    wellness_days_synced=7,
    fitness_days_synced=7
)

# Get sync history
history = repo.get_sync_history(user_id, limit=10)
last_success = repo.get_last_successful_sync(user_id)

# Get users needing auto-sync
users_to_sync = repo.get_all_auto_sync_users()

# Delete credentials
repo.delete_credentials(user_id)
```

---

### AIUsageRepository

**File**: `src/db/repositories/ai_usage_repository.py`

Tracks AI API usage, costs, and rate limiting.

```python
from training_analyzer.db.repositories import get_ai_usage_repository

repo = get_ai_usage_repository()

# Log AI request (async pattern - start then complete)
log = repo.log_request(
    request_id="req_123",
    user_id="usr_abc123",
    model_id="gpt-4o-mini",
    analysis_type="workout_analysis",
    entity_type="workout",
    entity_id="workout_456"
)

# Complete the request with results
repo.update_request(
    request_id="req_123",
    status="completed",
    input_tokens=1000,
    output_tokens=500
)

# Or log complete usage in one call
repo.log_usage(
    request_id="req_789",
    user_id="usr_abc123",
    model_id="gpt-4o-mini",
    input_tokens=1000,
    output_tokens=500,
    total_cost_cents=0,  # Auto-calculated from pricing table
    analysis_type="chat",
    duration_ms=1500
)

# Get usage summary
summary = repo.get_usage_summary(user_id)
# Returns: total_requests, total_tokens, total_cost_cents, by_model, by_type

# Get usage history
history = repo.get_usage_by_date_range(
    user_id,
    start_date=date(2024, 1, 1),
    end_date=date.today()
)

# Check rate limits
limits = repo.get_usage_limits(
    user_id,
    daily_request_limit=100,
    daily_cost_limit_cents=500,
    monthly_cost_limit_cents=5000
)
if limits.is_rate_limited:
    raise HTTPException(429, "Rate limit exceeded")

# Get recent logs
logs = repo.get_recent_logs(user_id, limit=20)
```

**Model Pricing** (default):

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4o | $2.50 | $10.00 |

---

## Singleton Pattern

All repositories use the singleton pattern for efficiency:

```python
_user_repository: Optional[UserRepository] = None

def get_user_repository() -> UserRepository:
    """Get or create the UserRepository singleton."""
    global _user_repository
    if _user_repository is None:
        _user_repository = UserRepository()
    return _user_repository
```

## Testing

Each repository has comprehensive tests in `tests/`:

| File | Tests | Coverage |
|------|-------|----------|
| `test_user_repository.py` | 41 | User CRUD, sessions, pagination |
| `test_subscription_repository.py` | 40 | Plans, subscriptions, usage |
| `test_garmin_credentials_repository.py` | 32 | Credentials, sync config/history |
| `test_ai_usage_repository.py` | 34 | Logging, costs, rate limits |

Run tests:
```bash
cd training-analyzer
python3 -m pytest tests/test_*_repository.py -v
```

## Related Documentation

- [MULTI_USER_ARCHITECTURE.md](./MULTI_USER_ARCHITECTURE.md) - System overview
- [AUTHENTICATION.md](./AUTHENTICATION.md) - JWT auth service
- [TESTING.md](./TESTING.md) - Full test documentation
