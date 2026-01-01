# Testing Documentation

This document describes the test coverage for the multi-user database features.

## Overview

The multi-user database implementation includes **229 tests** across 6 test files, all passing.

## Test Files

| File | Tests | Coverage |
|------|-------|----------|
| `test_user_repository.py` | 41 | User CRUD, sessions, pagination |
| `test_subscription_repository.py` | 40 | Plans, subscriptions, usage tracking |
| `test_garmin_credentials_repository.py` | 32 | Credentials, sync config, history |
| `test_ai_usage_repository.py` | 34 | Request logging, costs, rate limits |
| `test_feature_gate.py` | 43 | Feature limits, tier checking |
| `test_auth_service.py` | 39 | JWT tokens, password hashing |

## Running Tests

### All Multi-User Tests

```bash
cd training-analyzer
python3 -m pytest tests/test_user_repository.py \
    tests/test_subscription_repository.py \
    tests/test_garmin_credentials_repository.py \
    tests/test_ai_usage_repository.py \
    tests/test_feature_gate.py \
    tests/test_auth_service.py \
    -v
```

### Individual Test File

```bash
python3 -m pytest tests/test_user_repository.py -v
```

### Specific Test Class

```bash
python3 -m pytest tests/test_user_repository.py::TestUserCreation -v
```

### Specific Test

```bash
python3 -m pytest tests/test_user_repository.py::TestUserCreation::test_create_user_minimal -v
```

### With Coverage Report

```bash
python3 -m pytest tests/test_user_repository.py --cov=training_analyzer --cov-report=html
```

## Test Details

### test_user_repository.py (41 tests)

**TestUserRepositoryInit** (2 tests)
- `test_creates_users_table` - Users table created on init
- `test_creates_email_index` - Email index created

**TestUserCreation** (5 tests)
- `test_create_user_minimal` - Create with required fields only
- `test_create_user_with_all_fields` - Create with all fields
- `test_create_user_duplicate_email_fails` - Email uniqueness
- `test_create_user_duplicate_id_fails` - ID uniqueness
- `test_create_user_timestamps` - Created/updated timestamps

**TestUserRetrieval** (5 tests)
- `test_get_by_id` - Retrieve by ID
- `test_get_by_id_not_found` - Returns None if not found
- `test_get_by_email` - Retrieve by email
- `test_get_by_email_not_found` - Returns None if not found
- `test_get_by_email_case_sensitive` - Case sensitivity

**TestUserUpdate** (9 tests)
- `test_update_single_field` - Update one field
- `test_update_multiple_fields` - Update multiple fields
- `test_update_email` - Update email address
- `test_update_password_hash` - Update password
- `test_update_admin_status` - Update admin flag
- `test_update_active_status` - Update active flag
- `test_update_nonexistent_user` - Returns None
- `test_update_no_fields` - No-op update
- `test_update_changes_updated_at` - Timestamp updated

**TestUserDeletion** (2 tests)
- `test_delete_user` - Delete existing user
- `test_delete_nonexistent_user` - Returns False

**TestLoginTracking** (3 tests)
- `test_update_last_login` - Updates timestamp
- `test_update_last_login_multiple_times` - Successive updates
- `test_update_last_login_nonexistent_user` - Returns False

**TestUserExistence** (4 tests)
- `test_exists_true` - Existing user
- `test_exists_false` - Non-existent user
- `test_email_exists_true` - Existing email
- `test_email_exists_false` - Non-existent email

**TestUserListing** (5 tests)
- `test_get_all_active_only` - Default active filter
- `test_get_all_including_inactive` - Include inactive
- `test_get_all_with_limit` - Pagination limit
- `test_get_all_with_offset` - Pagination offset
- `test_get_all_ordered_by_created_at` - Sort order

**TestUserCount** (3 tests)
- `test_count_active_only` - Count active users
- `test_count_all` - Count all users
- `test_count_empty` - Empty table

**TestUserDataclass** (1 test)
- `test_user_defaults` - Default values

**TestSingletonPattern** (1 test)
- `test_get_user_repository_returns_singleton` - Singleton behavior

---

### test_subscription_repository.py (40 tests)

**TestSubscriptionRepositoryInit** (4 tests)
- Table creation and default plans

**TestSubscriptionPlans** (5 tests)
- Free plan limits
- Pro plan unlimited
- Plan retrieval

**TestUserSubscriptions** (10 tests)
- Create subscription
- With Stripe integration
- With trial period
- Update plan/status
- Cancel at period end

**TestUsageTracking** (9 tests)
- Increment different features
- Cumulative tracking
- Create records on first use

**TestUsageLimitChecking** (6 tests)
- Under/at/over limits
- Pro unlimited access
- No subscription defaults

**TestUsageReset** (2 tests)
- Reset all counters
- Reset non-existent

**TestSubscriptionDataclasses** (3 tests)
- Default values for dataclasses

**TestSingletonPattern** (1 test)
- Singleton behavior

---

### test_garmin_credentials_repository.py (32 tests)

**TestGarminCredentialsRepositoryInit** (4 tests)
- Table creation
- Index creation

**TestCredentialStorage** (6 tests)
- Save minimal credentials
- Save with Garmin info
- Upsert behavior
- Retrieve credentials
- Delete credentials

**TestValidationStatus** (3 tests)
- Valid status
- Invalid with error
- Non-existent user

**TestSyncConfiguration** (4 tests)
- Get/update config
- Default values
- Partial updates

**TestSyncHistory** (9 tests)
- Start sync
- Complete success/failure/partial
- History limit and ordering
- Last successful sync

**TestAutoSyncUsers** (2 tests)
- Empty list
- Filter by valid credentials and enabled

**TestDataclasses** (3 tests)
- Default values

**TestSingletonPattern** (1 test)
- Singleton behavior

---

### test_ai_usage_repository.py (34 tests)

**TestAIUsageRepositoryInit** (4 tests)
- Table creation
- Default pricing

**TestRequestLogging** (4 tests)
- Pending requests
- Complete requests
- Failed requests

**TestUsageLogging** (4 tests)
- Complete logging
- Cost calculation
- Cached responses

**TestCostCalculation** (3 tests)
- GPT-4o-mini pricing
- GPT-4o pricing
- Unknown model

**TestUsageSummary** (4 tests)
- Aggregated summary
- By type/model breakdown
- Date range

**TestUsageHistory** (4 tests)
- Date range queries
- By analysis type
- Different granularities

**TestUsageLimits** (3 tests)
- Get limits
- Rate limited check

**TestRecentLogs** (3 tests)
- Retrieve recent
- Limit parameter
- Sort order

**TestDataclasses** (4 tests)
- Default values
- Total tokens property

**TestSingletonPattern** (1 test)
- Singleton behavior

---

### test_feature_gate.py (43 tests)

**TestFeatureEnum** (1 test)
- All features defined

**TestSubscriptionLimits** (4 tests)
- Free tier limits
- Free tier disabled features
- Pro unlimited
- Enterprise unlimited

**TestCanUseFeature** (10 tests)
- No usage
- Under/at/over limits
- Daily vs monthly limits
- Disabled features
- Pro unlimited
- Unknown tier

**TestUsageIncrement** (4 tests)
- Create usage record
- Cumulative increments
- Multiple features
- Multiple users

**TestUsageReset** (2 tests)
- Daily counter reset
- Monthly counter reset

**TestUsageSummary** (4 tests)
- Summary content
- At limit indicator
- Unlimited features

**TestCheckAndIncrement** (4 tests)
- Success case
- Monthly limit 402
- Daily limit 402
- Disabled feature 402

**TestFeatureAvailability** (3 tests)
- Free tier availability
- Pro tier availability
- Unknown tier

**TestDataclasses** (2 tests)
- Default values

**TestModuleFunctions** (9 tests)
- Singleton pattern
- Convenience functions

---

### test_auth_service.py (39 tests)

**TestAuthServiceInit** (1 test)
- Settings initialization

**TestAccessTokenCreation** (4 tests)
- Create token
- Token claims
- Additional claims
- Expiration time

**TestRefreshTokenCreation** (3 tests)
- Create token
- Token claims
- Expiration time

**TestTokenPairCreation** (3 tests)
- Create pair
- Expires in value
- Additional claims

**TestTokenVerification** (7 tests)
- Verify valid token
- With expected type
- Wrong type raises
- Access token verification
- Refresh token verification

**TestTokenExpiration** (1 test)
- Expired token raises

**TestInvalidTokenHandling** (3 tests)
- Invalid token raises
- Malformed token raises
- Wrong signature raises

**TestPasswordHashing** (5 tests)
- Hash password
- Unique hashes (salt)
- Verify correct
- Verify incorrect
- Invalid hash format

**TestDataclasses** (2 tests)
- TokenPayload structure
- TokenPair structure

**TestExceptions** (3 tests)
- Exception hierarchy
- Error messages

**TestModuleFunctions** (7 tests)
- Singleton pattern
- Convenience functions

## Test Fixtures

Common fixtures used across tests:

```python
@pytest.fixture
def temp_db_path():
    """Create temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    os.unlink(db_path)

@pytest.fixture
def user_repo(temp_db_path):
    """Create repository with temp database."""
    return UserRepository(db_path=temp_db_path)

@pytest.fixture
def sample_user(user_repo):
    """Create sample user for testing."""
    return user_repo.create_user(
        user_id="test-user-123",
        email="test@example.com",
        ...
    )
```

## Known Warnings

The tests produce some deprecation warnings that can be addressed in future updates:

1. **datetime.utcnow()**: Should use `datetime.now(datetime.UTC)`
2. **Pydantic class-based config**: Should use `ConfigDict`

These don't affect test functionality and are cosmetic improvements.

## Continuous Integration

Add to CI pipeline:

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: |
          cd training-analyzer
          python -m pytest tests/test_*_repository.py tests/test_feature_gate.py tests/test_auth_service.py -v --cov=training_analyzer
```

## Related Documentation

- [MULTI_USER_ARCHITECTURE.md](./MULTI_USER_ARCHITECTURE.md) - System overview
- [REPOSITORY_LAYER.md](./REPOSITORY_LAYER.md) - Repository documentation
- [AUTHENTICATION.md](./AUTHENTICATION.md) - Auth service
- [FEATURE_GATING.md](./FEATURE_GATING.md) - Feature gate service
