# Authentication Service

This document describes the JWT-based authentication service for the Training Analyzer application.

## Overview

The authentication service provides:

- **JWT Access Tokens**: Short-lived tokens for API authentication
- **JWT Refresh Tokens**: Long-lived tokens for session renewal
- **Password Hashing**: Secure bcrypt password storage
- **Token Verification**: Signature and expiration validation

## Configuration

Set these environment variables in `.env`:

```bash
# Required
JWT_SECRET_KEY=your-secret-key-here  # Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"

# Optional (defaults shown)
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

## Usage

### Creating Tokens

```python
from training_analyzer.services.auth_service import (
    get_auth_service,
    create_access_token,
    create_refresh_token,
)

# Using the service directly
auth = get_auth_service()
access_token = auth.create_access_token(
    user_id="usr_abc123",
    email="athlete@example.com",
    additional_claims={"tier": "pro", "role": "user"}
)

refresh_token = auth.create_refresh_token(user_id="usr_abc123")

# Or create a token pair
token_pair = auth.create_token_pair(
    user_id="usr_abc123",
    email="athlete@example.com"
)
# Returns: TokenPair(access_token, refresh_token, token_type="bearer", expires_in=1800)

# Using convenience functions
access_token = create_access_token("usr_abc123", "athlete@example.com")
refresh_token = create_refresh_token("usr_abc123")
```

### Verifying Tokens

```python
from training_analyzer.services.auth_service import (
    verify_token,
    TokenExpiredError,
    InvalidTokenError,
)

try:
    # Verify any token
    payload = verify_token(token)
    user_id = payload["sub"]
    email = payload.get("email")
    token_type = payload["type"]  # "access" or "refresh"

    # Verify with expected type
    payload = verify_token(token, expected_type="access")

    # Or use specific methods
    payload = auth.verify_access_token(token)
    payload = auth.verify_refresh_token(token)

except TokenExpiredError:
    # Token has expired - use refresh token to get new access token
    pass

except InvalidTokenError:
    # Token is malformed, wrong signature, or wrong type
    pass
```

### Password Hashing

```python
from training_analyzer.services.auth_service import hash_password, verify_password

# Hash a password (uses bcrypt)
hashed = hash_password("user_password_123")
# Returns: "$2b$12$..."

# Verify a password
if verify_password("user_password_123", hashed):
    print("Password correct")
else:
    print("Password incorrect")
```

## Token Structure

### Access Token Claims

```json
{
  "sub": "usr_abc123",           // User ID
  "email": "athlete@example.com", // User email
  "type": "access",              // Token type
  "iat": 1704067200,             // Issued at (Unix timestamp)
  "exp": 1704069000,             // Expires at (Unix timestamp)
  // Additional claims passed to create_access_token:
  "tier": "pro",
  "role": "user"
}
```

### Refresh Token Claims

```json
{
  "sub": "usr_abc123",  // User ID
  "type": "refresh",    // Token type
  "iat": 1704067200,    // Issued at
  "exp": 1704672000     // Expires at (7 days later)
}
```

## API Integration

### FastAPI Dependency

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from training_analyzer.services.auth_service import verify_token, InvalidTokenError, TokenExpiredError

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Dependency to get current authenticated user."""
    try:
        payload = verify_token(credentials.credentials, expected_type="access")
        return {
            "user_id": payload["sub"],
            "email": payload.get("email"),
            "tier": payload.get("tier", "free")
        }
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )

# Use in routes
@app.get("/api/me")
async def get_profile(user: dict = Depends(get_current_user)):
    return {"user_id": user["user_id"], "email": user["email"]}
```

### Token Refresh Endpoint

```python
@app.post("/api/auth/refresh")
async def refresh_tokens(refresh_token: str):
    """Exchange refresh token for new access token."""
    try:
        payload = verify_token(refresh_token, expected_type="refresh")
        user_id = payload["sub"]

        # Get user email from database
        user = user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(401, "User not found or inactive")

        # Create new token pair
        token_pair = auth.create_token_pair(user_id, user.email)
        return token_pair

    except (TokenExpiredError, InvalidTokenError):
        raise HTTPException(401, "Invalid refresh token")
```

## Security Considerations

1. **Secret Key**: Use a strong, random secret key (32+ bytes)
2. **HTTPS**: Always use HTTPS in production
3. **Token Storage**: Store tokens securely on client (httpOnly cookies or secure storage)
4. **Short Expiry**: Access tokens expire in 30 minutes by default
5. **Refresh Rotation**: Consider rotating refresh tokens on each use
6. **Blacklisting**: Implement token blacklist for logout (not yet implemented)

## Data Classes

```python
@dataclass
class TokenPayload:
    sub: str                    # User ID
    email: Optional[str]        # User email (access token only)
    exp: datetime               # Expiration time
    iat: datetime               # Issued at time
    type: str                   # "access" or "refresh"

@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800      # Seconds until access token expires
```

## Exceptions

```python
class AuthServiceError(Exception):
    """Base exception for auth service errors."""

class TokenExpiredError(AuthServiceError):
    """Token has expired."""

class InvalidTokenError(AuthServiceError):
    """Token is invalid (malformed, wrong signature, wrong type)."""
```

## Testing

The auth service has 39 tests covering:

- Token creation (access, refresh, pairs)
- Token verification and validation
- Token expiration handling
- Invalid token handling
- Password hashing and verification
- Singleton pattern

Run tests:
```bash
python3 -m pytest tests/test_auth_service.py -v
```

## Related Documentation

- [MULTI_USER_ARCHITECTURE.md](./MULTI_USER_ARCHITECTURE.md) - System overview
- [FEATURE_GATING.md](./FEATURE_GATING.md) - Subscription-based access control
- [REPOSITORY_LAYER.md](./REPOSITORY_LAYER.md) - User repository
