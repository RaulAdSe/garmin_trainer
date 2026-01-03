'use client';

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useRouter } from 'next/navigation';

// API base URL - direct to backend since CORS is configured
const API_BASE = 'http://localhost:8000/api/v1';

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
  register: (email: string, password: string, displayName?: string) => Promise<void>;
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

  // Logout function - defined first to avoid circular dependency
  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    setToken(null);
    setUser(null);
    router.push('/login');
  }, [router]);

  // Refresh token
  const refreshToken = useCallback(async (): Promise<boolean> => {
    const refresh = localStorage.getItem(REFRESH_KEY);
    if (!refresh) {
      logout();
      return false;
    }
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh })
      });
      if (res.ok) {
        const { access_token, refresh_token } = await res.json();
        localStorage.setItem(TOKEN_KEY, access_token);
        localStorage.setItem(REFRESH_KEY, refresh_token);
        setToken(access_token);
        return true;
      } else {
        logout();
        return false;
      }
    } catch (error) {
      // Network error - don't logout, might be temporary
      console.error('[Auth] Network error during token refresh:', error);
      return false;
    }
  }, [logout]);

  // Fetch user profile
  const fetchUser = useCallback(async (accessToken: string) => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${accessToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        // Map backend response to our User interface
        setUser({
          user_id: data.user.id,
          email: data.user.email,
          subscription_tier: data.user.subscription_tier as 'free' | 'pro' | 'enterprise',
          is_admin: data.user.is_admin,
        });
      } else if (res.status === 401) {
        // Try refresh
        const refreshed = await refreshToken();
        if (refreshed) {
          const newToken = localStorage.getItem(TOKEN_KEY);
          if (newToken) {
            try {
              const retryRes = await fetch(`${API_BASE}/auth/me`, {
                headers: { Authorization: `Bearer ${newToken}` }
              });
              if (retryRes.ok) {
                const data = await retryRes.json();
                setUser({
                  user_id: data.user.id,
                  email: data.user.email,
                  subscription_tier: data.user.subscription_tier as 'free' | 'pro' | 'enterprise',
                  is_admin: data.user.is_admin,
                });
              }
            } catch (retryError) {
              console.error('[Auth] Network error on retry:', retryError);
            }
          }
        }
      }
    } catch (e) {
      // Network error - backend might be down
      console.error('[Auth] Network error fetching user profile. Is the backend running?', e);
    } finally {
      setIsLoading(false);
    }
  }, [refreshToken]);

  // Load token on mount
  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY);
    if (storedToken) {
      setToken(storedToken);
      fetchUser(storedToken);
    } else {
      setIsLoading(false);
    }
  }, [fetchUser]);

  // Login
  async function login(email: string, password: string) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Login failed');
    }
    const { access_token, refresh_token } = await res.json();
    localStorage.setItem(TOKEN_KEY, access_token);
    localStorage.setItem(REFRESH_KEY, refresh_token);
    setToken(access_token);
    // Fetch user profile after successful login
    await fetchUser(access_token);
  }

  // Register
  async function register(email: string, password: string, displayName?: string) {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, display_name: displayName })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Registration failed');
    }
    const { access_token, refresh_token } = await res.json();
    localStorage.setItem(TOKEN_KEY, access_token);
    localStorage.setItem(REFRESH_KEY, refresh_token);
    setToken(access_token);
    // Fetch user profile after successful registration
    await fetchUser(access_token);
  }

  return (
    <AuthContext.Provider value={{
      user,
      token,
      isLoading,
      login,
      register,
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
