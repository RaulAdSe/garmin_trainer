import { useState, useCallback, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getGarminSyncHistory,
  triggerManualSync,
  getGarminCredentialStatus,
} from '@/lib/api-client';
import type { GarminSyncHistoryEntry } from '@/lib/types';

export interface DataFreshnessState {
  /** The last sync time as a Date object, or null if never synced */
  lastSyncTime: Date | null;
  /** Whether the data is considered stale based on threshold */
  isStale: boolean;
  /** Whether a sync is currently in progress */
  isSyncing: boolean;
  /** Whether the user has credentials configured for sync */
  hasCredentials: boolean;
  /** Error message if sync failed */
  error: string | null;
  /** Human-readable relative time string */
  relativeTimeString: string;
  /** Trigger a manual sync */
  refresh: () => Promise<void>;
  /** Whether loading initial data */
  isLoading: boolean;
}

interface UseDataFreshnessOptions {
  /** Threshold in hours after which data is considered stale (default: 72 = 3 days) */
  staleThresholdHours?: number;
  /** Whether to auto-refresh the relative time string */
  autoRefreshInterval?: number;
}

/**
 * Hook to manage data freshness state for the training analyzer.
 * Tracks when data was last synced from Garmin and provides refresh functionality.
 */
export function useDataFreshness(options: UseDataFreshnessOptions = {}): DataFreshnessState {
  const {
    staleThresholdHours = 72, // 3 days default
    autoRefreshInterval = 60000, // Update relative time every minute
  } = options;

  const queryClient = useQueryClient();
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [, setTick] = useState(0); // Force re-render for relative time updates

  // Fetch sync history to get last sync time
  const { data: syncHistory, isLoading: historyLoading } = useQuery({
    queryKey: ['garminSyncHistory'],
    queryFn: () => getGarminSyncHistory(1), // Only need the most recent
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });

  // Fetch credential status to check if sync is possible
  const { data: credentialStatus, isLoading: credentialLoading } = useQuery({
    queryKey: ['garminCredentialStatus'],
    queryFn: getGarminCredentialStatus,
    staleTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
  });

  // Auto-refresh relative time display
  useEffect(() => {
    const interval = setInterval(() => {
      setTick((t) => t + 1);
    }, autoRefreshInterval);
    return () => clearInterval(interval);
  }, [autoRefreshInterval]);

  // Extract the last sync time from history
  const lastSyncEntry = syncHistory?.[0];
  const lastSyncTime = lastSyncEntry?.completed_at
    ? new Date(lastSyncEntry.completed_at)
    : lastSyncEntry?.started_at
    ? new Date(lastSyncEntry.started_at)
    : null;

  // Check if data is stale
  const isStale = lastSyncTime
    ? Date.now() - lastSyncTime.getTime() > staleThresholdHours * 60 * 60 * 1000
    : true; // No sync = stale

  // Check if credentials are configured
  const hasCredentials = credentialStatus?.connected ?? false;

  // Generate relative time string
  const relativeTimeString = getRelativeTimeString(lastSyncTime);

  // Refresh function to trigger a manual sync
  const refresh = useCallback(async () => {
    if (!hasCredentials) {
      setSyncError('No Garmin credentials configured');
      return;
    }

    setIsSyncing(true);
    setSyncError(null);

    try {
      await triggerManualSync();
      // Invalidate queries to refresh data
      await queryClient.invalidateQueries({ queryKey: ['garminSyncHistory'] });
      await queryClient.invalidateQueries({ queryKey: ['athleteContext'] });
      await queryClient.invalidateQueries({ queryKey: ['workouts'] });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Sync failed';
      setSyncError(errorMessage);
    } finally {
      setIsSyncing(false);
    }
  }, [hasCredentials, queryClient]);

  return {
    lastSyncTime,
    isStale,
    isSyncing,
    hasCredentials,
    error: syncError,
    relativeTimeString,
    refresh,
    isLoading: historyLoading || credentialLoading,
  };
}

/**
 * Generate a human-readable relative time string.
 * Examples: "just now", "2h ago", "Yesterday", "3 days ago"
 */
function getRelativeTimeString(date: Date | null): string {
  if (!date) {
    return 'Never synced';
  }

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) {
    return 'just now';
  }

  if (diffMinutes < 60) {
    return `${diffMinutes}m ago`;
  }

  if (diffHours < 24) {
    return `${diffHours}h ago`;
  }

  if (diffDays === 1) {
    return 'Yesterday';
  }

  if (diffDays < 7) {
    return `${diffDays} days ago`;
  }

  if (diffDays < 30) {
    const weeks = Math.floor(diffDays / 7);
    return `${weeks} week${weeks === 1 ? '' : 's'} ago`;
  }

  if (diffDays < 365) {
    const months = Math.floor(diffDays / 30);
    return `${months} month${months === 1 ? '' : 's'} ago`;
  }

  const years = Math.floor(diffDays / 365);
  return `${years} year${years === 1 ? '' : 's'} ago`;
}

export default useDataFreshness;
