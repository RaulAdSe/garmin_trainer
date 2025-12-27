/**
 * React hooks for accessing wellness data.
 * These replace the API route calls for the Capacitor version.
 */

import { useState, useEffect, useCallback } from 'react';
import { wellness, TodayData } from './wellness';
import { garmin } from './garmin';
import { db } from './database';
import { Capacitor } from '@capacitor/core';

// Check if running in Capacitor (native) or browser
export function isNative(): boolean {
  return Capacitor.isNativePlatform();
}

// DayData type matching what the page expects
export interface DayData {
  date: string;
  sleep: {
    total_hours: number;
    deep_pct: number;
    rem_pct: number;
    score: number | null;
    efficiency: number | null;
    direction?: {
      direction: 'up' | 'down' | 'stable';
      change_pct: number;
      baseline: number;
      current: number;
    } | null;
  } | null;
  hrv: {
    value: number | null;
    baseline: number | null;
    status: string | null;
    direction?: {
      direction: 'up' | 'down' | 'stable';
      change_pct: number;
      baseline: number;
      current: number;
    } | null;
  };
  strain: {
    body_battery_charged: number | null;
    body_battery_drained: number | null;
    stress_avg: number | null;
    active_calories: number | null;
    intensity_minutes: number | null;
    direction?: {
      direction: 'up' | 'down' | 'stable';
      change_pct: number;
      baseline: number;
      current: number;
    } | null;
  };
  activity: {
    steps: number;
    steps_goal: number;
  };
  resting_hr: number | null;
  rhr_direction?: {
    direction: 'up' | 'down' | 'stable';
    change_pct: number;
    baseline: number;
    current: number;
  } | null;
  baselines?: {
    hrv_7d_avg: number | null;
    hrv_30d_avg: number | null;
    hrv_90d_avg: number | null;
    sleep_7d_avg: number | null;
    sleep_30d_avg: number | null;
    sleep_90d_avg: number | null;
    rhr_7d_avg: number | null;
    rhr_30d_avg: number | null;
    rhr_90d_avg: number | null;
    recovery_7d_avg: number | null;
    recovery_90d_avg: number | null;
  };
  // Extended fields for today's view
  recovery?: number;
  insight?: {
    decision: string;
    headline: string;
    explanation: string;
    strain_target: [number, number];
    sleep_target: number;
  };
  sleep_debt?: number;
  weekly_summary?: {
    green_days: number;
    yellow_days: number;
    red_days: number;
    avg_recovery: number;
    avg_strain: number;
    avg_sleep: number;
    total_sleep_debt: number;
    best_day: string;
    worst_day: string;
    correlations: Array<{
      pattern_type: 'positive' | 'negative';
      category: string;
      title: string;
      description: string;
      impact: number;
      confidence: number;
      sample_size: number;
    }>;
    streaks: Array<{
      name: string;
      current_count: number;
      best_count: number;
      is_active: boolean;
      last_date: string;
    }>;
    trend_alerts: Array<{
      metric: string;
      direction: 'declining' | 'improving';
      days: number;
      change_pct: number;
      severity: 'warning' | 'concern' | 'positive';
    }>;
  };
}

// Hook to fetch wellness history
export function useWellnessHistory(days: number = 14) {
  const [history, setHistory] = useState<DayData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        // Initialize database
        await db.initialize();

        // Get history from database
        const rawHistory = await wellness.getHistory(days);

        // Convert to DayData format
        const converted: DayData[] = rawHistory.map(h => ({
          date: h.date,
          sleep: h.sleep_hours ? {
            total_hours: h.sleep_hours,
            deep_pct: 0, // Would need raw data for this
            rem_pct: 0,
            score: null,
            efficiency: null,
            direction: null,
          } : null,
          hrv: {
            value: h.hrv,
            baseline: null,
            status: null,
            direction: null,
          },
          strain: {
            body_battery_charged: h.body_battery,
            body_battery_drained: null,
            stress_avg: null,
            active_calories: null,
            intensity_minutes: null,
            direction: null,
          },
          activity: {
            steps: h.steps,
            steps_goal: 10000,
          },
          resting_hr: h.resting_hr,
          rhr_direction: null,
          recovery: h.recovery,
        }));

        setHistory(converted);
      } catch (err) {
        console.error('Failed to load wellness history:', err);
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [days]);

  return { history, loading, error };
}

// Hook to get today's detailed data
export function useToday() {
  const [data, setData] = useState<TodayData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      await db.initialize();
      const todayData = await wellness.getToday();
      setData(todayData);
    } catch (err) {
      console.error('Failed to load today data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { data, loading, error, refresh };
}

// Hook for Garmin auth and sync
export function useGarminSync() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [progress, setProgress] = useState<{ current: number; total: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Check auth status on mount
  useEffect(() => {
    async function checkAuth() {
      const auth = await garmin.isAuthenticated();
      setIsAuthenticated(auth);
    }
    checkAuth();
  }, []);

  const login = async (email: string, password: string): Promise<boolean> => {
    setError(null);
    const result = await garmin.login(email, password);
    if (result.success) {
      setIsAuthenticated(true);
      return true;
    } else {
      setError(result.error || 'Login failed');
      return false;
    }
  };

  const logout = async () => {
    await garmin.logout();
    setIsAuthenticated(false);
  };

  const sync = async (days: number = 7): Promise<boolean> => {
    if (!isAuthenticated) {
      setError('Not authenticated');
      return false;
    }

    setSyncing(true);
    setProgress({ current: 0, total: days });
    setError(null);

    try {
      // Try backend sync first (uses Python garminconnect library)
      const result = await garmin.syncViaBackend(days, (current, total) => {
        setProgress({ current, total });
      });

      if (!result.success) {
        setError(result.error || 'Sync failed');
        return false;
      }

      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sync failed');
      return false;
    } finally {
      setSyncing(false);
      setProgress(null);
    }
  };

  return {
    isAuthenticated,
    syncing,
    progress,
    error,
    login,
    logout,
    sync,
  };
}

// Export a function to check if we need fallback data (for development)
export async function hasLocalData(): Promise<boolean> {
  try {
    await db.initialize();
    const stats = await db.getStats();
    return stats.total_days > 0;
  } catch {
    return false;
  }
}
