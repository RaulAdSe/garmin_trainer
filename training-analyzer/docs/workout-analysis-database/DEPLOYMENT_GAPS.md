# Deployment Gaps & Implementation Guide

This document identifies critical gaps blocking production deployment and provides simple, elegant solutions for each.

## Executive Summary

| Gap | Severity | Effort | Status |
|-----|----------|--------|--------|
| Frontend Auth Integration | CRITICAL | ~4 hours | Not Started |
| Route Auth Wiring | CRITICAL | ~2 hours | Not Started |
| Rate Limiting Middleware | HIGH | ~1 hour | Not Started |
| JWT Secret Hardening | HIGH | ~15 min | Not Started |
| CORS Hardening | MEDIUM | ~15 min | Not Started |

**Good News**: The backend auth infrastructure is 90% complete. The hard work (JWT, password hashing, dependency injection) is already done correctly.

---

## Gap 1: Frontend Auth Integration

### Current State

```
frontend/src/
├── app/providers.tsx          # Only has QueryClientProvider
├── lib/api-client.ts          # 100+ fetch calls, zero Authorization headers
└── components/                 # No auth guards, no token storage
```

### The Problem

- No `AuthContext` or `AuthProvider`
- No token storage (localStorage/sessionStorage)
- No token refresh logic
- No `Authorization: Bearer <token>` headers
- No protected route guards

### Elegant Solution

Create a minimal auth system with 3 files:

#### 1. Auth Context (`frontend/src/contexts/auth-context.tsx`)

```typescript
'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';

interface User {
  user_id: string;
  email: string;
  subscription_tier: 'free' | 'pro' | 'enterprise';
  is_admin: boolean;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

const TOKEN_KEY = 'ta_access_token';
const REFRESH_KEY = 'ta_refresh_token';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // Load token on mount
  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY);
    if (storedToken) {
      setToken(storedToken);
      fetchUser(storedToken);
    } else {
      setIsLoading(false);
    }
  }, []);

  // Fetch user profile
  async function fetchUser(accessToken: string) {
    try {
      const res = await fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${accessToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setUser(data.user);
      } else if (res.status === 401) {
        // Try refresh
        await refreshToken();
      }
    } catch (e) {
      console.error('Failed to fetch user', e);
    } finally {
      setIsLoading(false);
    }
  }

  // Refresh token
  async function refreshToken() {
    const refresh = localStorage.getItem(REFRESH_KEY);
    if (!refresh) {
      logout();
      return;
    }
    try {
      const res = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh })
      });
      if (res.ok) {
        const { access_token, refresh_token } = await res.json();
        localStorage.setItem(TOKEN_KEY, access_token);
        localStorage.setItem(REFRESH_KEY, refresh_token);
        setToken(access_token);
        await fetchUser(access_token);
      } else {
        logout();
      }
    } catch {
      logout();
    }
  }

  // Login
  async function login(email: string, password: string) {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Login failed');
    }
    const { access_token, refresh_token, user: userData } = await res.json();
    localStorage.setItem(TOKEN_KEY, access_token);
    localStorage.setItem(REFRESH_KEY, refresh_token);
    setToken(access_token);
    setUser(userData);
  }

  // Logout
  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    setToken(null);
    setUser(null);
    router.push('/login');
  }

  return (
    <AuthContext.Provider value={{
      user,
      token,
      isLoading,
      login,
      logout,
      isAuthenticated: !!user
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
```

#### 2. Authenticated Fetch (`frontend/src/lib/auth-fetch.ts`)

```typescript
const TOKEN_KEY = 'ta_access_token';

export async function authFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = localStorage.getItem(TOKEN_KEY);

  const headers = new Headers(options.headers);
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  return fetch(url, { ...options, headers });
}

// Drop-in replacement for existing fetch calls
export function createAuthenticatedClient() {
  return {
    get: (url: string) => authFetch(url),
    post: (url: string, data: unknown) => authFetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }),
    put: (url: string, data: unknown) => authFetch(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }),
    delete: (url: string) => authFetch(url, { method: 'DELETE' })
  };
}
```

#### 3. Protected Route (`frontend/src/components/auth/protected-route.tsx`)

```typescript
'use client';

import { useAuth } from '@/contexts/auth-context';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredTier?: 'free' | 'pro' | 'enterprise';
}

export function ProtectedRoute({ children, requiredTier }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

  if (!isAuthenticated) {
    return null;
  }

  // Check subscription tier if required
  if (requiredTier && user) {
    const tierRank = { free: 0, pro: 1, enterprise: 2 };
    if (tierRank[user.subscription_tier] < tierRank[requiredTier]) {
      return (
        <div className="flex items-center justify-center h-screen">
          <p>This feature requires {requiredTier} subscription</p>
        </div>
      );
    }
  }

  return <>{children}</>;
}
```

#### 4. Update Providers (`frontend/src/app/providers.tsx`)

```typescript
'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/contexts/auth-context';
import { useState } from 'react';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        {children}
      </AuthProvider>
    </QueryClientProvider>
  );
}
```

### Migration Path

1. Add the 3 new files
2. Update `providers.tsx`
3. Replace `fetch()` with `authFetch()` in `api-client.ts`
4. Wrap protected pages with `<ProtectedRoute>`

---

## Gap 2: Route Auth Wiring

### Current State

5 route files have this pattern:

```python
# src/api/routes/analysis.py, chat.py, workouts.py, usage.py, garmin_credentials.py

def get_current_user_id() -> Optional[str]:
    # TODO: Get from authentication context
    return "default"  # HARDCODED!
```

### The Solution Already Exists

The auth middleware is already built at `src/api/middleware/auth.py`:

```python
# This exists and works!
from src.api.deps import get_current_user, CurrentUser

@router.get("/me")
async def get_me(current_user: CurrentUser = Depends(get_current_user)):
    return {"user_id": current_user.user_id}
```

### Simple Fix

Replace hardcoded functions with the dependency injection pattern:

```python
# BEFORE (in each route file)
def get_current_user_id() -> Optional[str]:
    # TODO: Get from authentication context
    return "default"

@router.get("/data")
async def get_data():
    user_id = get_current_user_id()
    ...

# AFTER
from ..deps import get_current_user, CurrentUser

@router.get("/data")
async def get_data(current_user: CurrentUser = Depends(get_current_user)):
    user_id = current_user.user_id
    ...
```

### Files to Update

| File | Lines to Change | Pattern |
|------|-----------------|---------|
| `src/api/routes/analysis.py` | ~146, 251, 746 | Replace `get_current_user_id()` |
| `src/api/routes/chat.py` | ~100, 112 | Replace `get_current_user_id()` |
| `src/api/routes/garmin_credentials.py` | ~128, 152, 198, 221, 255, 288, 318, 354 | Replace `get_current_user_id()` |
| `src/api/routes/workouts.py` | ~1015 | Replace hardcoded `user_id = "default"` |
| `src/api/routes/usage.py` | ~138, 146+ | Replace `get_user_id()` |

### Automated Fix Script

```bash
# Find all TODOs related to auth
grep -rn "TODO.*auth" src/api/routes/ --include="*.py"

# Find all hardcoded "default" user
grep -rn 'return "default"' src/api/routes/ --include="*.py"
grep -rn 'user_id = "default"' src/api/routes/ --include="*.py"
```

---

## Gap 3: Rate Limiting Middleware

### Current State

- Config exists in `.env.example` but is unused
- No rate limiting library installed
- No middleware registered

### Elegant Solution: slowapi

#### 1. Install

```bash
pip install slowapi
```

Add to `requirements.txt`:
```
slowapi>=0.1.9
```

#### 2. Create Rate Limiter (`src/api/middleware/rate_limit.py`)

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from ..deps import get_optional_user

def get_rate_limit_key(request: Request) -> str:
    """Rate limit by user_id if authenticated, else by IP."""
    # Try to get user from token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from src.services.auth_service import get_auth_service
            token = auth_header[7:]
            payload = get_auth_service().verify_token(token)
            return f"user:{payload['sub']}"
        except:
            pass
    # Fall back to IP
    return f"ip:{get_remote_address(request)}"

limiter = Limiter(key_func=get_rate_limit_key)
```

#### 3. Register in Main App (`src/main.py`)

```python
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .api.middleware.rate_limit import limiter

app = FastAPI()

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

#### 4. Apply to Routes

```python
from ..middleware.rate_limit import limiter

@router.post("/analyze")
@limiter.limit("10/minute")  # AI endpoints: 10 req/min
async def analyze_workout(request: Request, ...):
    ...

@router.get("/workouts")
@limiter.limit("60/minute")  # Standard endpoints: 60 req/min
async def get_workouts(request: Request, ...):
    ...
```

### Rate Limit Tiers

| Endpoint Type | Free Tier | Pro Tier |
|---------------|-----------|----------|
| AI Analysis | 10/day | 100/day |
| AI Chat | 20/day | Unlimited |
| Standard API | 60/min | 120/min |
| Data Export | 5/day | Unlimited |

---

## Gap 4: JWT Secret Hardening

### Current State

```python
# src/config.py line 61
jwt_secret_key: str = "dev-secret-key-change-in-production"  # DANGER!
```

### Simple Fix

```python
# src/config.py
import os

class Settings(BaseSettings):
    # JWT - NO DEFAULT VALUE, must be set in environment
    jwt_secret_key: str = Field(
        ...,  # Required, no default
        description="JWT secret key - generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    )

    @field_validator('jwt_secret_key')
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if v == "dev-secret-key-change-in-production":
            raise ValueError("JWT secret must be changed from default value")
        if len(v) < 32:
            raise ValueError("JWT secret must be at least 32 characters")
        return v
```

### Environment Setup

```bash
# Generate a secure secret
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env
JWT_SECRET_KEY=your-generated-secret-here
```

---

## Gap 5: CORS Hardening

### Current State

```python
# src/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # localhost only
    allow_credentials=True,
    allow_methods=["*"],  # TOO PERMISSIVE
    allow_headers=["*"],  # TOO PERMISSIVE
)
```

### Production-Ready Fix

```python
# src/config.py
class Settings(BaseSettings):
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins"
    )
    cors_methods: list[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed HTTP methods"
    )
    cors_headers: list[str] = Field(
        default=["Authorization", "Content-Type", "Accept"],
        description="Allowed headers"
    )

# src/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)
```

### Production .env

```bash
CORS_ORIGINS=["https://training-analyzer.com","https://app.training-analyzer.com"]
CORS_METHODS=["GET","POST","PUT","DELETE","OPTIONS"]
CORS_HEADERS=["Authorization","Content-Type","Accept"]
```

---

## Implementation Order

### Phase 1: Backend Security (30 min)
1. Fix JWT secret validation (prevents deployment with insecure secret)
2. Harden CORS configuration
3. Add slowapi to requirements.txt

### Phase 2: Route Auth Wiring (2 hours)
1. Update all 5 route files to use `get_current_user` dependency
2. Test each endpoint with valid/invalid tokens
3. Verify feature gating works with real user tiers

### Phase 3: Rate Limiting (1 hour)
1. Create rate limit middleware
2. Register in main app
3. Apply limits to AI endpoints first
4. Add limits to standard endpoints

### Phase 4: Frontend Auth (4 hours)
1. Create AuthContext and AuthProvider
2. Create authFetch utility
3. Update api-client.ts to use authFetch
4. Add ProtectedRoute component
5. Create login/register pages
6. Wrap protected routes

---

## Testing Checklist

### Backend
- [ ] JWT secret validation rejects default value
- [ ] JWT secret validation rejects short secrets
- [ ] CORS blocks unauthorized origins
- [ ] Rate limiter blocks excessive requests
- [ ] All routes use `get_current_user` dependency
- [ ] Feature gating enforces subscription limits

### Frontend
- [ ] Login stores tokens in localStorage
- [ ] Auth headers sent with all API requests
- [ ] Token refresh works before expiration
- [ ] Logout clears all stored data
- [ ] Protected routes redirect to login
- [ ] Subscription tier gates premium features

### Integration
- [ ] Full login → use app → logout flow works
- [ ] Rate limits apply per-user when authenticated
- [ ] Rate limits apply per-IP when anonymous
- [ ] Multi-user data isolation verified

---

## Related Documentation

- [MULTI_USER_ARCHITECTURE.md](./MULTI_USER_ARCHITECTURE.md) - System overview
- [AUTHENTICATION.md](./AUTHENTICATION.md) - JWT auth service details
- [FEATURE_GATING.md](./FEATURE_GATING.md) - Subscription limits
- [TESTING.md](./TESTING.md) - Test coverage
