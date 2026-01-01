# Current Problems & Solutions - Authentication System

## Overview

This document describes authentication issues discovered during development and their solutions.

---

## Problem 1: JWT Token Signed with Wrong Secret

### Symptom
- API calls return `401 Unauthorized` even with a token present
- Direct curl to backend with token fails

### Root Cause
The JWT token stored in `localStorage` was generated with a different secret than what the backend uses. The backend reads `JWT_SECRET_KEY` from `/Users/rauladell/garmin_insights/.env`, but tokens were being generated with a hardcoded or different secret.

### Solution
Generate tokens using the correct secret from the `.env` file:

```python
import jwt
from datetime import datetime, timedelta, timezone

SECRET = 'YOUR_JWT_SECRET_KEY_FROM_ENV'  # From /Users/rauladell/garmin_insights/.env
payload = {
    'sub': 'dev-user-123',
    'email': 'dev@example.com',
    'subscription_tier': 'pro',
    'is_admin': True,
    'iat': datetime.now(timezone.utc),
    'exp': datetime.now(timezone.utc) + timedelta(days=365),
    'type': 'access'
}
token = jwt.encode(payload, SECRET, algorithm='HS256')
```

### Files Affected
- `/Users/rauladell/garmin_insights/.env` - Contains `JWT_SECRET_KEY`
- `src/services/auth_service.py` - Uses the secret for token validation

---

## Problem 2: Next.js Proxy Not Forwarding Authorization Headers

### Symptom
- API calls through `http://localhost:3000/api/v1/*` return `401`
- Same calls directly to `http://localhost:8000/api/v1/*` work fine
- Network tab shows requests going through but auth fails

### Root Cause
Next.js rewrites (`next.config.ts`) proxy requests to the backend, but the `Authorization` header is not forwarded properly. Additionally, FastAPI's `redirect_slashes=True` (default) caused 307 redirects that stripped the auth header.

### Solution
**Option A (Implemented):** Call backend directly instead of using Next.js proxy.

Changed `API_BASE` in `frontend/src/lib/api-client.ts`:
```typescript
// Before (using proxy)
const API_BASE = '/api/v1';

// After (direct backend call)
const API_BASE = 'http://localhost:8000/api/v1';
```

**Option B (Alternative):** Use middleware to forward headers:
```typescript
// middleware.ts
if (pathname.startsWith('/api')) {
    const requestHeaders = new Headers(request.headers);
    const authHeader = request.headers.get('Authorization');
    if (authHeader) {
        requestHeaders.set('Authorization', authHeader);
    }
    return NextResponse.next({
        request: { headers: requestHeaders },
    });
}
```

### Files Affected
- `frontend/src/lib/api-client.ts` - API base URL
- `frontend/src/app/[locale]/login/page.tsx` - Login endpoint URL
- `frontend/middleware.ts` - Header forwarding (if using Option B)
- `frontend/next.config.ts` - Rewrite configuration
- `src/main.py` - Added `redirect_slashes=False` to FastAPI

---

## Problem 3: Auth Routes Not Registered

### Symptom
- Login endpoint returns `404 Not Found`
- `/api/v1/auth/login` doesn't exist

### Root Cause
The `auth.router` was defined in `src/api/routes/auth.py` but not imported or registered in `src/main.py`.

### Solution
Added auth router to main.py:

```python
# Import
from .api.routes import ..., auth

# Register
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
```

### Files Affected
- `src/main.py` - Import and router registration

---

## Problem 4: No Default Dev User

### Symptom
- Login fails with "Invalid email or password"
- No way to authenticate without registering first

### Root Cause
The in-memory user store `_users` in `auth.py` is empty on startup.

### Solution
Added a default dev user that's created on module load:

```python
# src/api/routes/auth.py
def _init_dev_user() -> None:
    """Initialize a default dev user for local development."""
    from datetime import datetime, timezone
    dev_user_id = "dev-user-123"
    if dev_user_id not in _users:
        _users[dev_user_id] = {
            "id": dev_user_id,
            "email": "dev@example.com",
            "password_hash": hash_password("devpassword123"),
            "display_name": "Dev User",
            "subscription_tier": "pro",
            "is_admin": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

# Initialize on module load
_init_dev_user()
```

### Dev Credentials
- **Email:** `dev@example.com`
- **Password:** `devpassword123`

### Files Affected
- `src/api/routes/auth.py` - Dev user initialization

---

## Problem 5: Turbopack Cache Corruption

### Symptom
- `Failed to fetch` errors during navigation
- Missing build manifests
- RSC payload fetch failures
- Error: `TurbopackInternalError: Failed to restore task data`

### Root Cause
The Turbopack cache in `.next` directory became corrupted, possibly due to interrupted builds or system crashes.

### Solution
Clean rebuild:
```bash
cd frontend
rm -rf .next
npm run dev
```

Or use webpack instead of Turbopack (more stable):
```bash
npm run dev:webpack
```

### Files Affected
- `frontend/.next/` - Cache directory

---

## Quick Reference

### Starting the Development Environment

```bash
# Terminal 1: Backend
cd /Users/rauladell/garmin_insights/training-analyzer
source /Users/rauladell/garmin_insights/.venv/bin/activate
python -m src.main

# Terminal 2: Frontend
cd /Users/rauladell/garmin_insights/training-analyzer/frontend
npm run dev:webpack  # More stable than Turbopack
```

### Testing Authentication

```bash
# Test login endpoint
curl -X POST -H "Content-Type: application/json" \
  -d '{"email":"dev@example.com","password":"devpassword123"}' \
  http://localhost:8000/api/v1/auth/login

# Test authenticated endpoint
TOKEN="your_token_here"
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/workouts/?page=1&pageSize=2
```

### Setting Token Manually (Browser Console)

```javascript
// Set token
localStorage.setItem('ta_access_token', 'YOUR_TOKEN');
location.reload();

// Check token
localStorage.getItem('ta_access_token')?.substring(0, 60);

// Clear tokens
localStorage.removeItem('ta_access_token');
localStorage.removeItem('ta_refresh_token');
```

---

## Architecture Notes

### Token Flow
1. User submits credentials to `/api/v1/auth/login`
2. Backend validates and returns `access_token` + `refresh_token`
3. Frontend stores tokens in `localStorage` with key `ta_access_token`
4. `authFetch()` wrapper adds `Authorization: Bearer <token>` to all API calls
5. Backend validates token in `get_current_user` dependency

### Key Files
| File | Purpose |
|------|---------|
| `frontend/src/lib/auth-fetch.ts` | Token storage and fetch wrapper |
| `frontend/src/contexts/auth-context.tsx` | React auth context and hooks |
| `frontend/src/app/[locale]/login/page.tsx` | Login page component |
| `src/api/routes/auth.py` | Auth endpoints (login, register, refresh) |
| `src/api/middleware/auth.py` | `get_current_user` dependency |
| `src/services/auth_service.py` | JWT creation and validation |

### Environment Variables
| Variable | Location | Purpose |
|----------|----------|---------|
| `JWT_SECRET_KEY` | `/Users/rauladell/garmin_insights/.env` | JWT signing secret |
| `JWT_ALGORITHM` | Config default: `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Config default: `30` | Token TTL |

---

## TODO / Future Improvements

- [ ] Implement automatic token refresh when access token expires
- [ ] Add proper session management with refresh token rotation
- [ ] Consider using HTTP-only cookies instead of localStorage for tokens
- [ ] Add rate limiting to auth endpoints (currently exists but verify)
- [ ] Implement proper user registration flow
- [ ] Add password reset functionality
- [ ] Consider switching to Supabase Auth for production
