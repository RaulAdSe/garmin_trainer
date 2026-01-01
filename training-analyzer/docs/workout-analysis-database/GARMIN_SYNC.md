# Garmin Sync Service

This document describes the Garmin Connect integration with encrypted credential storage and automatic synchronization.

## Overview

The Garmin sync system provides:

- **Encrypted Credentials**: Fernet encryption for stored passwords
- **Auto-Sync Scheduler**: Configurable automatic data synchronization
- **Sync History**: Detailed tracking of sync operations
- **Per-User Configuration**: Individual sync settings per user

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Garmin Sync System                                │
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   Frontend   │───▶│  API Routes  │───▶│  Encryption  │              │
│  │  (Settings)  │    │ /garmin/*    │    │   Service    │              │
│  └──────────────┘    └──────────────┘    └──────┬───────┘              │
│                                                  │                       │
│                                                  ▼                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   Garmin     │◀───│   Garmin     │◀───│  Credentials │              │
│  │   Connect    │    │  Scheduler   │    │  Repository  │              │
│  │    API       │    │ (APScheduler)│    │              │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│                             │                                           │
│                             ▼                                           │
│                      ┌──────────────┐                                  │
│                      │ Sync History │                                  │
│                      │  Repository  │                                  │
│                      └──────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Credential Encryption

### How It Works

1. User provides Garmin email/password via frontend
2. API encrypts credentials using Fernet symmetric encryption
3. Encrypted values stored in database
4. When syncing, credentials are decrypted in-memory only
5. Decrypted values never logged or stored

### Encryption Service

```python
from training_analyzer.services.encryption import EncryptionService

# Initialize with key from environment
encryption = EncryptionService()

# Encrypt credentials
encrypted_email = encryption.encrypt("user@example.com")
encrypted_password = encryption.encrypt("garmin_password")

# Decrypt when needed
email = encryption.decrypt(encrypted_email)
password = encryption.decrypt(encrypted_password)
```

### Configuration

Set the encryption key in `.env`:

```bash
# Generate a key:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
CREDENTIAL_ENCRYPTION_KEY=your-fernet-key-here
```

### Security Considerations

- Encryption key stored only in environment, never in code/database
- Fernet provides authenticated encryption (AES-128-CBC + HMAC-SHA256)
- Key rotation supported via `encryption_key_id` field
- Failed validation marks credentials as invalid without deleting

## Storing Credentials

```python
from training_analyzer.db.repositories import get_garmin_credentials_repository
from training_analyzer.services.encryption import get_encryption_service

repo = get_garmin_credentials_repository()
encryption = get_encryption_service()

# Encrypt and store
creds = repo.save_credentials(
    user_id="usr_abc123",
    encrypted_email=encryption.encrypt(email),
    encrypted_password=encryption.encrypt(password),
    encryption_key_id="v1",
    garmin_user_id="garmin_12345",      # From Garmin API response
    garmin_display_name="JohnDoe"
)

# Retrieve and decrypt
creds = repo.get_credentials(user_id)
if creds and creds.is_valid:
    email = encryption.decrypt(creds.encrypted_email)
    password = encryption.decrypt(creds.encrypted_password)
```

## Sync Configuration

Each user can configure their sync preferences:

```python
# Update sync configuration
config = repo.update_sync_config(
    user_id="usr_abc123",
    auto_sync_enabled=True,
    sync_frequency="daily",      # "hourly", "daily", "weekly"
    sync_time="06:00",           # Time for daily syncs (UTC)
    sync_activities=True,        # Sync activity data
    sync_wellness=True,          # Sync wellness data (sleep, stress)
    sync_fitness_metrics=True,   # Sync fitness metrics (VO2max, etc.)
    initial_sync_days=365,       # Days of history for first sync
    incremental_sync_days=7,     # Days to check on incremental syncs
    min_sync_interval_minutes=60 # Minimum time between syncs
)

# Get configuration
config = repo.get_sync_config(user_id)
```

### Default Configuration

| Setting | Default |
|---------|---------|
| `auto_sync_enabled` | `True` |
| `sync_frequency` | `"daily"` |
| `sync_time` | `"06:00"` |
| `sync_activities` | `True` |
| `sync_wellness` | `True` |
| `sync_fitness_metrics` | `True` |
| `initial_sync_days` | `365` |
| `incremental_sync_days` | `7` |
| `min_sync_interval_minutes` | `60` |

## Auto-Sync Scheduler

The scheduler runs automatic syncs based on user configuration:

```python
from training_analyzer.services.garmin_scheduler import GarminSyncScheduler

# Initialize scheduler
scheduler = GarminSyncScheduler()

# Start the scheduler (typically in app startup)
scheduler.start()

# Stop the scheduler (in app shutdown)
scheduler.stop()

# Manually trigger sync for a user
scheduler.sync_user(user_id)

# Get next scheduled sync time
next_sync = scheduler.get_next_sync_time(user_id)
```

### Scheduler Configuration

```bash
# .env settings
GARMIN_SYNC_ENABLED=true
GARMIN_SYNC_HOUR=6          # Hour (UTC) for daily syncs
GARMIN_SYNC_MAX_RETRIES=3   # Retries on failure
```

## Sync History

Track all sync operations:

```python
# Start a sync operation
sync_id = repo.start_sync(
    user_id="usr_abc123",
    sync_type="scheduled",  # "manual", "scheduled", "initial"
    sync_from_date=date(2024, 1, 1),
    sync_to_date=date.today()
)

# Complete the sync
repo.complete_sync(
    sync_id=sync_id,
    status="completed",     # "completed", "failed", "partial"
    activities_synced=15,
    wellness_days_synced=7,
    fitness_days_synced=7,
    error_message=None,     # Set if status is "failed" or "partial"
    error_details=None      # JSON with error details
)

# Get sync history
history = repo.get_sync_history(user_id, limit=10)
for entry in history:
    print(f"{entry.started_at}: {entry.status}")
    print(f"  Activities: {entry.activities_synced}")
    print(f"  Duration: {entry.duration_seconds}s")

# Get last successful sync
last_success = repo.get_last_successful_sync(user_id)
if last_success:
    print(f"Last sync: {last_success.completed_at}")
```

### Sync Status Values

| Status | Description |
|--------|-------------|
| `running` | Sync in progress |
| `completed` | Sync finished successfully |
| `partial` | Some data synced, some failed |
| `failed` | Sync completely failed |

## Validation

Validate stored credentials:

```python
# After attempting to use credentials
if login_failed:
    repo.update_validation_status(
        user_id,
        is_valid=False,
        validation_error="Invalid credentials or account locked"
    )
else:
    repo.update_validation_status(
        user_id,
        is_valid=True,
        validation_error=None
    )

# Check validation status
creds = repo.get_credentials(user_id)
if not creds.is_valid:
    print(f"Invalid since: {creds.last_validation_at}")
    print(f"Error: {creds.validation_error}")
```

## Finding Users to Sync

```python
# Get all users with valid credentials and auto-sync enabled
users_to_sync = repo.get_all_auto_sync_users()

for user_id in users_to_sync:
    config = repo.get_sync_config(user_id)
    last_sync = repo.get_last_successful_sync(user_id)

    # Check if sync is needed based on config and last sync
    if should_sync(config, last_sync):
        scheduler.sync_user(user_id)
```

## Database Tables

### garmin_credentials

| Column | Type | Description |
|--------|------|-------------|
| `user_id` | TEXT | User ID (primary key) |
| `encrypted_email` | TEXT | Fernet-encrypted email |
| `encrypted_password` | TEXT | Fernet-encrypted password |
| `encryption_key_id` | TEXT | Key version for rotation |
| `garmin_user_id` | TEXT | Garmin account ID |
| `garmin_display_name` | TEXT | Garmin display name |
| `is_valid` | INTEGER | 1 if credentials work |
| `last_validation_at` | TEXT | Last validation time |
| `validation_error` | TEXT | Error message if invalid |

### garmin_sync_config

| Column | Type | Description |
|--------|------|-------------|
| `user_id` | TEXT | User ID (primary key) |
| `auto_sync_enabled` | INTEGER | Enable auto-sync |
| `sync_frequency` | TEXT | hourly/daily/weekly |
| `sync_time` | TEXT | Time for daily syncs |
| `sync_activities` | INTEGER | Sync activities |
| `sync_wellness` | INTEGER | Sync wellness data |
| `sync_fitness_metrics` | INTEGER | Sync fitness metrics |
| `initial_sync_days` | INTEGER | Days for initial sync |
| `incremental_sync_days` | INTEGER | Days for incremental |
| `min_sync_interval_minutes` | INTEGER | Min time between syncs |

### garmin_sync_history

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Auto-increment ID |
| `user_id` | TEXT | User ID |
| `sync_type` | TEXT | manual/scheduled/initial |
| `started_at` | TEXT | Sync start time |
| `completed_at` | TEXT | Sync end time |
| `duration_seconds` | INTEGER | Total duration |
| `status` | TEXT | running/completed/partial/failed |
| `activities_synced` | INTEGER | Count of activities |
| `wellness_days_synced` | INTEGER | Days of wellness data |
| `fitness_days_synced` | INTEGER | Days of fitness data |
| `error_message` | TEXT | Error summary |
| `error_details` | TEXT | JSON error details |

## Testing

The Garmin credentials repository has 32 tests covering:

- Credential storage and retrieval
- Encryption key versioning
- Upsert behavior
- Validation status updates
- Sync configuration management
- Sync history tracking
- Auto-sync user listing

Run tests:
```bash
python3 -m pytest tests/test_garmin_credentials_repository.py -v
```

## Related Documentation

- [MULTI_USER_ARCHITECTURE.md](./MULTI_USER_ARCHITECTURE.md) - System overview
- [REPOSITORY_LAYER.md](./REPOSITORY_LAYER.md) - Repository documentation
- [AUTHENTICATION.md](./AUTHENTICATION.md) - User authentication
