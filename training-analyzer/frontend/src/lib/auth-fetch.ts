const TOKEN_KEY = 'ta_access_token';
const REFRESH_KEY = 'ta_refresh_token';
const API_BASE = 'http://localhost:8000/api/v1';

// Track if a token refresh is in progress to avoid multiple simultaneous refresh attempts
let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

/**
 * Check if a token exists in localStorage (client-side only).
 * Use this to determine if API calls requiring auth should be made.
 */
export function hasAuthToken(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }
  const token = localStorage.getItem(TOKEN_KEY);
  return !!token && token.length > 0;
}

/**
 * Create a mock 401 Unauthorized Response.
 * Used when we know auth will fail to avoid unnecessary network calls.
 */
function createUnauthorizedResponse(): Response {
  return new Response(
    JSON.stringify({
      message: 'Not authenticated',
      code: 'UNAUTHENTICATED',
    }),
    {
      status: 401,
      statusText: 'Unauthorized',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );
}

/**
 * Attempt to refresh the access token using the stored refresh token.
 * Returns true if refresh was successful, false otherwise.
 *
 * Uses a singleton pattern to prevent multiple simultaneous refresh attempts.
 */
async function refreshAccessToken(): Promise<boolean> {
  // If already refreshing, wait for that to complete
  if (isRefreshing && refreshPromise) {
    return refreshPromise;
  }

  const refreshToken = localStorage.getItem(REFRESH_KEY);
  if (!refreshToken) {
    return false;
  }

  isRefreshing = true;
  refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem(TOKEN_KEY, data.access_token);
        localStorage.setItem(REFRESH_KEY, data.refresh_token);
        return true;
      }

      // Refresh failed - clear tokens to trigger re-login
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_KEY);
      return false;
    } catch {
      // Network error during refresh - don't clear tokens, might be temporary
      return false;
    } finally {
      isRefreshing = false;
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/**
 * Fetch wrapper that automatically adds Authorization Bearer headers
 * for authenticated API requests.
 *
 * Features:
 * - If no token is present, returns a mock 401 response immediately
 * - If the server returns 401, automatically attempts to refresh the token
 * - If refresh succeeds, retries the original request with the new token
 * - If refresh fails, returns the 401 response
 */
export async function authFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null;

  // Early return with mock 401 if no token is present
  if (!token) {
    return createUnauthorizedResponse();
  }

  const headers = new Headers(options.headers);
  headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(url, { ...options, headers });

  // If we get a 401, try to refresh the token and retry
  if (response.status === 401) {
    const refreshed = await refreshAccessToken();

    if (refreshed) {
      // Get the new token and retry the request
      const newToken = localStorage.getItem(TOKEN_KEY);
      if (newToken) {
        const retryHeaders = new Headers(options.headers);
        retryHeaders.set('Authorization', `Bearer ${newToken}`);
        return fetch(url, { ...options, headers: retryHeaders });
      }
    }

    // Refresh failed, return the original 401 response
    // Note: We need to return a new response since the original may have been consumed
    return createUnauthorizedResponse();
  }

  return response;
}

/**
 * Authenticated API client with helper methods for common HTTP operations.
 * Use as a drop-in replacement for fetch calls that need authentication.
 */
export function createAuthenticatedClient() {
  return {
    /**
     * Perform an authenticated GET request
     */
    get: (url: string, options?: RequestInit) => authFetch(url, { ...options, method: 'GET' }),

    /**
     * Perform an authenticated POST request with JSON body
     */
    post: <T = unknown>(url: string, data: T, options?: RequestInit) =>
      authFetch(url, {
        ...options,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(options?.headers || {}),
        },
        body: JSON.stringify(data),
      }),

    /**
     * Perform an authenticated PUT request with JSON body
     */
    put: <T = unknown>(url: string, data: T, options?: RequestInit) =>
      authFetch(url, {
        ...options,
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...(options?.headers || {}),
        },
        body: JSON.stringify(data),
      }),

    /**
     * Perform an authenticated DELETE request
     */
    delete: (url: string, options?: RequestInit) =>
      authFetch(url, { ...options, method: 'DELETE' }),

    /**
     * Perform an authenticated PATCH request with JSON body
     */
    patch: <T = unknown>(url: string, data: T, options?: RequestInit) =>
      authFetch(url, {
        ...options,
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...(options?.headers || {}),
        },
        body: JSON.stringify(data),
      }),
  };
}

// Export a singleton client instance for convenience
export const apiClient = createAuthenticatedClient();
