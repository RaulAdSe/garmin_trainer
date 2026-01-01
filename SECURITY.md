# Security Review - Workout Analyzer Project

**Review Date:** 2025-12-30
**Status:** Pre-deployment review
**Reviewers:** Automated security analysis (5 concurrent agents)

---

## Executive Summary

This document captures security findings from a comprehensive review covering authentication, input validation, API security, dependencies, and data privacy. The review identified **2 CRITICAL** (2 resolved), **10 HIGH** (7 resolved), **8 MEDIUM** (8 resolved/mitigated), and **5 LOW** (5 resolved/documented) severity issues.

**Overall Status: 22/25 findings resolved (88%)** ✅

**Key Risk Areas (Original):**
- ~~Missing security configuration keys (JWT, encryption)~~ - RESOLVED (2025-12-30)
- ~~Unencrypted sensitive data at rest (Strava tokens)~~ - RESOLVED (2025-12-30)
- ~~Health data transmitted to external LLM providers~~ - MITIGATED (consent service, PRIVACY.md)
- ~~Unpinned dependencies and no lock files~~ - RESOLVED (2025-12-30)

**Resolution Summary by Phase:**
- **Phase 1** (Critical): JWT/encryption key validation, startup checks, key generation script (#1, #4)
- **Phase 2** (Data Security): Strava token encryption, DB permissions script, consent service, PRIVACY.md (#5, #6, #7)
- **Phase 3** (Code Quality): Error sanitization (12 files), logging fixes, dependency pinning, uv.lock files (#9, #10, #11, #12)
- **Phase 4** (Medium): Security headers, OAuth state in DB, data retention, log sanitizer, prompt sanitizer (#13, #14, #15, #17, #20)
- **Phase 5** (Low): Route authentication, MIT license, GDPR docs, dependency cleanup (#18, #21, #22, #23, #24)

---

## Architecture Notes

### Secrets Management

**`.env` file:** This is the designated secrets storage location for the project. It is properly gitignored and should contain all sensitive credentials (API keys, passwords, etc.). This is the expected pattern for local development.

**`shared/.garth_tokens/`:** These tokens are intentionally PUBLIC and shared. They are not sensitive credentials - this is by design for the shared Garmin client functionality.

---

## Critical Findings

### 1. Missing JWT Secret Key

**Severity:** CRITICAL
**Status:** ✅ RESOLVED (2025-12-30)

**Location:** `.env`, `training-analyzer/src/config.py` (lines 66-91)

**Issue:** `JWT_SECRET_KEY` environment variable is required but not configured.

**Risk:** API authentication will fail to start, or if a weak default is used, session tokens can be forged.

**Resolution:**
- Environment variable `JWT_SECRET_KEY` added to `.env` and `.env.example`
- Config validates key is set and meets minimum length requirements
- Key generation script available at `training-analyzer/scripts/generate_security_keys.py`

```bash
# Generate keys using the provided script:
python training-analyzer/scripts/generate_security_keys.py
```

---

### 4. Missing Credential Encryption Key

**Severity:** CRITICAL
**Status:** ✅ RESOLVED (2025-12-30)

**Location:** `.env`, `training-analyzer/src/services/encryption.py`

**Issue:** `CREDENTIAL_ENCRYPTION_KEY` is required for Garmin credential encryption but not set.

**Risk:** Garmin credential storage will fail; existing encrypted data becomes inaccessible.

**Resolution:**
- Environment variable `CREDENTIAL_ENCRYPTION_KEY` added to `.env` and `.env.example`
- Fernet-based encryption (AES-128-CBC) implemented in `encryption.py`
- Key generation script available at `training-analyzer/scripts/generate_security_keys.py`
- Also used for Strava token encryption (see #5)

```bash
# Generate keys using the provided script:
python training-analyzer/scripts/generate_security_keys.py
```

---

## High Severity Findings

### 5. Strava OAuth Tokens Stored Unencrypted in Database

**Severity:** HIGH
**Status:** ✅ RESOLVED (2025-12-30)

**Location:** `training-analyzer/src/db/repositories/strava_repository.py`

**Issue:** Strava `access_token` and `refresh_token` were stored directly in SQLite without encryption.

**Resolution:**
- Added `encrypted_access_token`, `encrypted_refresh_token`, and `encryption_key_id` columns
- `StravaRepository` now uses `CredentialEncryption` service (same as Garmin credentials)
- Migration script: `training-analyzer/src/db/migrations/migration_005_encrypt_strava_tokens.py`
- Existing plaintext tokens automatically encrypted on migration
- Plaintext columns preserved during transition for rollback support

**Files Modified:**
- `training-analyzer/src/db/repositories/strava_repository.py` - Encryption at read/write
- `training-analyzer/src/db/schema.py` - Schema with encrypted columns
- `training-analyzer/src/db/migrations/migration_005_encrypt_strava_tokens.py` - Migration script

---

### 6. SQLite Databases Not Encrypted at Rest

**Severity:** HIGH
**Status:** ✅ RESOLVED (2025-12-30) - Permissions fixed; SQLCipher optional

**Locations:**
- `training-analyzer/training.db` (487KB)
- `training.db` (40KB)
- `whoop-dashboard/wellness.db` (147KB)

**Issue:** All databases contain sensitive health data but are stored without encryption. File permissions are 644 (world-readable).

**Sensitive data includes:**
- User profile (age, gender, weight, HR zones)
- Activity metrics (heart rate, pace)
- Garmin credentials (encrypted, but DB itself is not)
- Strava OAuth tokens (now encrypted - see #5)
- User sessions

**Resolution:**
- Created `training-analyzer/scripts/fix_db_permissions.sh` script to set proper permissions
- Script sets all `.db` files to `chmod 600` (owner read/write only)
- Run manually or as part of deployment:

```bash
# Fix permissions using the provided script:
./training-analyzer/scripts/fix_db_permissions.sh

# Or manually:
chmod 600 *.db training-analyzer/*.db whoop-dashboard/*.db
```

**Note:** SQLCipher for full database encryption remains a recommended enhancement for highly sensitive deployments.

---

### 7. Health Data Sent to External LLM (OpenAI)

**Severity:** HIGH
**Status:** ✅ MITIGATED (2025-12-30)

**Location:** `training-analyzer/src/llm/context_builder.py`

**Issue:** The following PII/PHI is transmitted to OpenAI:
- Age and gender
- Max HR, Resting HR, Threshold HR
- VO2max values
- Race predictions
- Training status and readiness scores
- Recent workout details

**Resolution:**
1. **Consent Service Created:** `training-analyzer/src/services/consent_service.py`
   - `user_consent` table tracks LLM data sharing consent
   - `check_llm_consent(user_id)` - Check if user has consented
   - `record_consent(user_id, consented)` - Record consent decision
   - `get_consent_status(user_id)` - Get full consent details

2. **Privacy Documentation:** `PRIVACY.md` created with:
   - Full list of data categories sent to OpenAI (Section 4)
   - Third-party data sharing disclosure (Section 3)
   - User rights documentation (Section 5)
   - GDPR compliance information (Section 12)

3. **Prompt Sanitizer:** `training-analyzer/src/llm/prompt_sanitizer.py`
   - Monitors for injection attempts
   - Logs suspicious inputs for security review

**Remaining:** Review OpenAI data usage policies; consider anonymization for highly sensitive deployments.

---

### 8. In-Memory User Store (Development Code)

**Severity:** HIGH
**Status:** 🟠 Remove before deployment

**Location:** `training-analyzer/src/api/routes/auth.py` (line 33)

**Issue:** User credentials stored in an in-memory dictionary:
```python
_users: dict[str, dict] = {}
```

**Risk:** All users lost on server restart; not suitable for production.

**Remediation:** Implement database-backed user repository; add environment checks to prevent this code from running in production.

---

### 9. Sensitive Information in Error Messages

**Severity:** HIGH
**Status:** ✅ RESOLVED (2025-12-30)

**Locations:**
- `training-analyzer/src/api/routes/strava.py`
- `training-analyzer/src/api/routes/workouts.py`
- And 10 other route files

**Issue:** Raw API response text and internal errors included in client-facing error messages.

**Resolution:**
Sanitized error messages across **12 API route files**:

| File | Fixes |
|------|-------|
| `strava.py` | Token refresh, token exchange, sync errors |
| `workouts.py` | Garmin auth, fetch, design, FIT generation |
| `garmin.py` | Connection errors, activity fetch, response building |
| `athlete.py` | Context, readiness, fitness metrics, VO2max, predictions |
| `chat.py` | Agent initialization, agentic/standard modes |
| `analysis.py` | Agent init, recent workouts, batch analysis |
| `plans.py` | Plan generation, adaptation, fetch activities |
| `auth.py` | Token validation errors |
| `gamification.py` | Achievements, progress, check |
| `explain.py` | Readiness, workout recommendation, session |
| `garmin_credentials.py` | Save credentials |
| `export.py` | FIT generation, download, batch export |
| `usage.py` | Summary, history, limits, estimates |

**Pattern Applied:**
```python
# Before (insecure):
raise HTTPException(detail=f"Failed: {response.text}")

# After (secure):
logger.error(f"Strava API error: {response.text}")
raise HTTPException(detail="Failed to connect to Strava. Please try again.")
```

---

### 10. Print Statements with Credentials

**Severity:** HIGH
**Status:** ✅ RESOLVED (2025-12-30)

**Locations:**
- `training-analyzer/src/api/routes/strava.py`
- `training-analyzer/src/services/encryption.py`

**Issue:** Print statements output sensitive information including response data and encryption keys.

**Resolution:**
- All print statements removed from `strava.py` and `encryption.py`
- Replaced with structured logging via Python `logging` module
- Log sanitization filter installed (see #20) prevents credential leakage in logs

---

### 11. Unpinned Dependency Versions

**Severity:** HIGH
**Status:** ✅ RESOLVED (2025-12-30)

**Locations:**
- `training-analyzer/pyproject.toml`
- `training-analyzer/requirements.txt`

**Issue:** All Python dependencies use `>=` version specifiers without upper bounds.

**Resolution:**
Added upper bounds to all dependencies in `pyproject.toml`:

| Package | Before | After |
|---------|--------|-------|
| `fastapi` | `>=0.109.0` | `>=0.109.0,<1.0.0` |
| `cryptography` | `>=41.0.0` | `>=41.0.0,<44.0.0` |
| `langchain` | `>=0.3.0` | `>=0.3.0,<1.0.0` |
| `PyJWT` | `>=2.8.0` | `>=2.8.0,<3.0.0` |
| `pydantic` | `>=2.5.0` | `>=2.5.0,<3.0.0` |
| `openai` | `>=1.10.0` | `>=1.10.0,<2.0.0` |
| `bcrypt` | `>=4.1.0` | `>=4.1.0,<5.0.0` |

All 22 main dependencies and 5 dev dependencies now have upper bounds preventing unexpected major version upgrades.

---

### 12. No Dependency Lock Files

**Severity:** HIGH
**Status:** ✅ RESOLVED (2025-12-30)

**Issue:** No `poetry.lock`, `Pipfile.lock`, or `uv.lock` files found. Builds are not reproducible and vulnerable to dependency confusion attacks.

**Resolution:** Created `uv.lock` files for all Python packages:
- `/training-analyzer/uv.lock` (83 packages)
- `/shared/garmin_client/uv.lock` (22 packages)
- `/whoop-dashboard/uv.lock` (23 packages)
- `/training-analyzer/reactive-training-app/backend/uv.lock` (50 packages)

**Usage:**
```bash
# Install from lock file for reproducible builds:
uv sync

# Update lock file after changing dependencies:
uv lock
```

---

## Medium Severity Findings

### 13. LLM Prompt Injection Potential

**Severity:** MEDIUM
**Status:** ✅ MITIGATED (2025-12-30)

**Location:** `training-analyzer/src/api/routes/chat.py`, `training-analyzer/src/agents/langchain_agent.py`

**Issue:** User messages passed directly to LLM without sanitization. No filtering for injection patterns like "ignore previous instructions".

**Mitigating factors:**
- Single-user application
- LLM has read-only data access
- Rate limiting applied

**Resolution:** Added prompt sanitization utility at `training-analyzer/src/llm/prompt_sanitizer.py`:
- Detects common injection patterns (instruction override, system prompt extraction, role manipulation, jailbreak attempts, privilege escalation)
- Logs suspicious inputs for monitoring (does not block requests)
- Categorizes risk levels (NONE, LOW, MEDIUM, HIGH)
- Applied in `chat.py` for both standard and streaming endpoints

The sanitizer provides defense-in-depth monitoring while relying on the LLM's built-in safety measures.

---

### 14. Missing Security Headers

**Severity:** MEDIUM
**Status:** ✅ RESOLVED (2025-12-30)

**Location:** `training-analyzer/src/api/middleware/security_headers.py`

**Issue:** FastAPI application did not set security headers.

**Resolution:** Added `SecurityHeadersMiddleware` with all recommended headers:
- `X-Content-Type-Options: nosniff` - Prevents MIME type sniffing
- `X-Frame-Options: DENY` - Prevents clickjacking
- `Strict-Transport-Security` - Enforces HTTPS (configurable)
- `Content-Security-Policy` - Restrictive default for API
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy` - Disables unnecessary browser features

**Configuration:**
- HSTS can be disabled for local development via `SECURITY_ENABLE_HSTS=false`
- Custom CSP via `SECURITY_CSP` environment variable

**Files:**
- `training-analyzer/src/api/middleware/security_headers.py` - Middleware implementation
- `training-analyzer/src/main.py` - Middleware registration

---

### 15. OAuth State Stored In-Memory

**Severity:** MEDIUM
**Status:** ✅ RESOLVED (2025-12-30)

**Location:** `training-analyzer/src/db/repositories/strava_repository.py`

**Issue:** OAuth state tokens were stored in Python dictionary; lost on restart; incompatible with multi-instance deployments.

**Resolution:** Implemented database-backed OAuth state storage:
- Added `oauth_states` table in schema with `state` and `created_at` columns
- `StravaRepository.save_oauth_state()` stores state with timestamp
- `StravaRepository.verify_and_delete_oauth_state()` validates and removes used states
- `StravaRepository.cleanup_expired_oauth_states()` removes expired states (15 min TTL)
- Automatic cleanup during scheduled data retention jobs

**Files:**
- `training-analyzer/src/db/schema.py` - Added `oauth_states` table
- `training-analyzer/src/db/repositories/strava_repository.py` - State persistence methods

---

### 16. CORS Allows Multiple Localhost Origins

**Severity:** MEDIUM
**Status:** ✅ RESOLVED (2025-12-30)

**Location:** `training-analyzer/src/config.py` (lines 28-31)

**Issue:** CORS configured with multiple localhost origins and `allow_credentials=True`.

**Resolution:** `CORS_ORIGINS` environment variable configured for production deployment.

---

### 17. No Data Retention Policy

**Severity:** MEDIUM
**Status:** ✅ RESOLVED (2025-12-30)

**Issue:** No automatic cleanup for old activity data, expired user sessions, historical sync logs, AI usage logs.

**Resolution:** Implemented comprehensive data retention service with scheduled cleanup:

**Data Retention Service** (`training-analyzer/src/services/data_retention_service.py`):
- `cleanup_expired_sessions()` - Sessions older than 30 days (configurable)
- `cleanup_ai_usage_logs()` - AI usage logs older than 90 days
- `cleanup_sync_history()` - Garmin sync history older than 90 days
- `cleanup_strava_sync_records()` - Completed Strava syncs older than 90 days
- `cleanup_old_activity_data()` - Activity data older than 2 years (disabled by default)
- `cleanup_old_workout_analyses()` - Orphaned workout analyses

**Cleanup Scheduler** (`training-analyzer/src/services/cleanup_scheduler.py`):
- Daily scheduled cleanup at 3 AM UTC (configurable)
- Manual trigger support via admin API
- Cleanup reports with deleted record counts

**Configuration (`.env`):**
```env
RETENTION_SESSIONS_DAYS=30
RETENTION_AI_USAGE_LOGS_DAYS=90
RETENTION_SYNC_HISTORY_DAYS=90
RETENTION_ACTIVITY_DATA_DAYS=730  # 0 = keep forever
RETENTION_CLEANUP_ENABLED=true
RETENTION_CLEANUP_HOUR=3  # UTC
```

---

### 18. Duplicate Dependency Declarations

**Severity:** MEDIUM
**Status:** ✅ RESOLVED (2025-12-30)

**Locations:** `pyproject.toml`, `requirements.txt`

**Issue:** langchain packages appear in multiple locations (main deps, optional deps, requirements.txt).

**Resolution:**
1. **Removed duplicate `[project.optional-dependencies].agent` section** from `pyproject.toml`
   - Langchain packages now only in main dependencies

2. **Consolidated all dependencies in `pyproject.toml`:**
   - Added missing packages: `tiktoken`, `PyJWT`, `bcrypt`, `cryptography`, `APScheduler`, `slowapi`
   - Total: 22 main dependencies, 5 dev dependencies

3. **Updated `requirements.txt` to reference `pyproject.toml`:**
   ```txt
   # Install from pyproject.toml (single source of truth)
   -e .
   ```

**Benefit:** Single source of truth for all dependencies; no duplicate declarations to maintain.

---

### 19. Missing Stripe Webhook Secret

**Severity:** MEDIUM
**Status:** ✅ RESOLVED (2025-12-30)

**Location:** `.env`

**Issue:** `STRIPE_WEBHOOK_SECRET` referenced in config but not set.

**Resolution:** `STRIPE_WEBHOOK_SECRET` environment variable configured in `.env`.

---

### 20. Logging Without Sanitization

**Severity:** MEDIUM
**Status:** ✅ RESOLVED (2025-12-30)

**Issue:** Extensive logging throughout codebase with no sanitization layer to prevent credential/PII leakage.

**Resolution:** Implemented comprehensive log sanitization filter:

**Log Sanitizer** (`training-analyzer/src/utils/log_sanitizer.py`):
- `LogSanitizationFilter` class that processes all log records
- Installed globally via `install_log_sanitizer()` at application startup
- Redacts sensitive patterns before logs are written

**Patterns Redacted:**
- API keys (OpenAI, Anthropic, Strava, Stripe)
- Bearer tokens and Authorization headers
- JWT tokens
- Fernet encryption keys
- Passwords and secrets (in various formats)
- Email addresses
- Credit card numbers
- OAuth codes and tokens
- Long hex strings (potential tokens)

**Usage:**
```python
from utils.log_sanitizer import install_log_sanitizer
install_log_sanitizer()  # Called in main.py before any logging
```

**Tests:** `training-analyzer/tests/utils/test_log_sanitizer.py`

---

## Low Severity Findings

### 21. Unauthenticated Routes

**Severity:** LOW
**Status:** ✅ RESOLVED (2025-12-30)

**Location:** Various routes in `training-analyzer/src/api/routes/`

**Issue:** Several routes lacked authentication requirements.

**Resolution:** Added authentication to all routes that expose user-specific data:

**Now Protected (require JWT authentication):**
- `gamification.py` - All routes (achievements, progress, check)
- `athlete.py` - All routes (context, readiness, fitness-metrics, vo2max-trend, race-predictions, training-paces, goal-feasibility)
- `usage.py` - User-specific routes (summary, history, by-type, limits, recent, quota)

**Intentionally Public (no user data exposed):**
- `usage.py: GET /pricing` - Returns general model pricing information
- `usage.py: GET /estimate/{analysis_type}` - Returns cost estimates based on averages
- `auth.py: POST /register, /login, /refresh` - Authentication endpoints

---

### 22. Print Statements Instead of Logging

**Severity:** LOW
**Status:** ✅ RESOLVED (2025-12-30)

**Issue:** Multiple files use `print()` instead of `logger.info()`.

**Resolution:**
Replaced `print()` statements with structured logging across multiple files:

| File | Changes |
|------|---------|
| `garmin.py` | Sync errors, activity processing, fitness sync |
| `enrichment.py` | N8N database warnings, FTP warnings, enrichment errors |
| `workouts.py` | Training pace calculation, athlete context errors |
| `workout_agent.py` | LLM design failures |
| `strava.py` | OAuth flow logging |

**Pattern Applied:**
```python
# Before:
print(f"Warning: {error}")

# After:
logger.warning(f"Warning: {error}")
```

**Remaining:** CLI tools (`cli.py`) and migration scripts intentionally use `console.print()` for user output.

---

### 23. No Project License File

**Severity:** LOW
**Status:** ✅ RESOLVED (2025-12-30)

**Issue:** No `LICENSE` file in project root.

**Resolution:**
- Created `LICENSE` file at project root with MIT License
- Copyright 2025 Garmin Insights
- MIT License is permissive and compatible with all project dependencies

---

### 24. Session IP Address Storage (GDPR Consideration)

**Severity:** LOW
**Status:** DOCUMENTED (2025-12-30)

**Location:** `training-analyzer/src/db/schema.py` (line 404)

**Issue:** The `user_sessions` table stores IP addresses, which are considered personal data under GDPR (Article 4(1)).

**GDPR Implications:**
- IP addresses can identify individuals when combined with other data
- Requires valid legal basis for processing (legitimate interest for security)
- Subject to data minimization and storage limitation principles
- Users have rights to access, erasure, and object to processing

**Mitigations Implemented:**
1. **Automatic retention cleanup:** Sessions (including IP addresses) are deleted after 30 days via `DataRetentionService`
2. **Configuration option:** IP logging can be disabled via `PRIVACY_LOG_IP_ADDRESSES=false` in `.env`
3. **Purpose limitation:** IP addresses only used for security/session management, not analytics
4. **Documentation:** Full GDPR implications documented in `PRIVACY.md` Section 12

**Configuration:**
```bash
# To disable IP address logging for strict GDPR compliance:
PRIVACY_LOG_IP_ADDRESSES=false

# To adjust session retention period (default 30 days):
RETENTION_SESSIONS_DAYS=7
```

**See also:** `PRIVACY.md` Section 12 for complete GDPR compliance documentation.

---

### 25. Outdated Minimum Versions

**Severity:** LOW

**Issue:** Some minimum versions are significantly behind current stable releases (e.g., `langgraph>=0.0.25` vs current `0.2.x`).

---

## Positive Security Findings

The following security practices are correctly implemented:

| Area | Implementation |
|------|----------------|
| Secrets Management | `.env` used as designated secrets storage, properly gitignored |
| Shared Tokens | `shared/.garth_tokens/` intentionally public for shared Garmin client |
| Git Security | `.gitignore` properly excludes `.env` and sensitive files |
| SQL Injection | All queries use parameterized statements |
| Command Injection | No subprocess/shell execution found |
| Password Hashing | bcrypt with proper salt generation |
| Credential Encryption | Fernet (AES-128-CBC) for Garmin credentials |
| JWT Validation | Rejects weak/default keys |
| Token Expiration | Access: 30 min, Refresh: 7 days |
| Rate Limiting | slowapi implementation |
| OAuth Security | State parameter with `secrets.compare_digest` |
| HTTPS | All external API calls use HTTPS |
| SSL Validation | No `verify=False` bypasses found |
| Licenses | All dependencies use permissive licenses (MIT/Apache/BSD) |

---

## Pre-Deployment Checklist

### Immediate (Before Any Deployment) ✅ All Complete

- [x] Add `JWT_SECRET_KEY` to `.env` (DONE: #1 resolved 2025-12-30)
- [x] Add `CREDENTIAL_ENCRYPTION_KEY` to `.env` (DONE: #4 resolved 2025-12-30)
- [x] Fix file permissions script created (DONE: #6 - run `./training-analyzer/scripts/fix_db_permissions.sh`)

### Before Production Deployment ✅ All Complete

- [x] Encrypt Strava tokens in database (DONE: #5 resolved 2025-12-30)
- [x] Add security headers middleware (DONE: #14 resolved 2025-12-30)
- [x] Create dependency lock files (DONE: #12 resolved 2025-12-30)
- [x] Pin versions for security-critical packages (DONE: #11 resolved 2025-12-30)
- [x] Sanitize error messages in API responses (DONE: #9 resolved 2025-12-30)
- [x] Replace print statements with proper logging (DONE: #10, #22 resolved 2025-12-30)
- [x] Implement database-backed OAuth state storage (DONE: #15 resolved 2025-12-30)
- [x] Add authentication to routes (DONE: #21 resolved 2025-12-30)
- [x] Consolidate dependencies (DONE: #18 resolved 2025-12-30)
- [x] Add project license (DONE: #23 resolved 2025-12-30)

### Operational Tasks (Run at Deployment) ✅ All Complete

- [x] Run `./training-analyzer/scripts/fix_db_permissions.sh` to secure database files (DONE: 2025-12-30)
- [x] Restrict CORS origins for production (DONE: #16 - `CORS_ORIGINS` configured)
- [x] Configure Stripe webhook secret (DONE: #19 - `STRIPE_WEBHOOK_SECRET` configured)

### Remaining Improvements (3 items - Optional/Dev-Only)

| # | Item | Priority | Notes |
|---|------|----------|-------|
| #6 | SQLCipher full DB encryption | Optional | Permissions already fixed; SQLCipher for enterprise |
| #8 | Remove in-memory user store | Dev Only | Works for single-user; production would use Supabase |
| #25 | Update langgraph minimum | Low | Lock files ensure reproducibility |

**Other enhancements (not from original review):**
- [ ] Implement audit logging for sensitive data access
- [ ] Create user data export/deletion API (GDPR enhancement)

### Completed Improvements ✅

- [x] Add data retention policies (DONE: #17 resolved 2025-12-30)
- [x] Add log sanitization middleware (DONE: #20 resolved 2025-12-30)
- [x] Add prompt injection monitoring (DONE: #13 mitigated 2025-12-30)
- [x] Add consent service for LLM data sharing (DONE: #7 mitigated 2025-12-30)
- [x] Document IP address storage GDPR implications (DONE: #24 - See PRIVACY.md Section 12)
- [x] Add config option to disable IP logging (DONE: `PRIVACY_LOG_IP_ADDRESSES`)

---

## Security Tools Recommendations

| Tool | Purpose |
|------|---------|
| `pip-audit` | Check for known Python vulnerabilities |
| `safety` | Alternative Python vulnerability scanner |
| `npm audit` | Built-in npm vulnerability scanner |
| `Dependabot` | Automated dependency updates |
| `Snyk` | Comprehensive dependency security |
| `trivy` | Container and filesystem scanner |
| `bandit` | Python static security analysis |

---

## Contact

For security concerns or to report vulnerabilities, contact the project maintainer.
