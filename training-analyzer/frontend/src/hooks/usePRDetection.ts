'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useCallback, useEffect } from 'react';
import {
  getPersonalRecords,
  getRecentPRs,
  detectPRs,
  getPRSummary,
  compareToPRs,
} from '@/lib/api-client';
import type { PRType, PRCelebrationData } from '@/components/emotional/PRCelebrationModal';

/**
 * Query keys for PR-related queries
 */
export const prKeys = {
  all: ['personalRecords'] as const,
  list: (prType?: PRType, activityType?: string) =>
    [...prKeys.all, 'list', { prType, activityType }] as const,
  recent: (days: number) => [...prKeys.all, 'recent', days] as const,
  summary: () => [...prKeys.all, 'summary'] as const,
  compare: (workoutId: string) => [...prKeys.all, 'compare', workoutId] as const,
};

/**
 * Hook for fetching all personal records with optional filtering
 */
export function usePRHistory(prType?: PRType, activityType?: string) {
  return useQuery({
    queryKey: prKeys.list(prType, activityType),
    queryFn: () => getPersonalRecords({ prType, activityType }),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook for fetching recent personal records (last N days)
 */
export function useRecentPRs(days: number = 30) {
  return useQuery({
    queryKey: prKeys.recent(days),
    queryFn: () => getRecentPRs(days),
    staleTime: 60 * 1000, // 1 minute
  });
}

/**
 * Hook for fetching PR summary
 */
export function usePRSummary() {
  return useQuery({
    queryKey: prKeys.summary(),
    queryFn: getPRSummary,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook for comparing a workout to existing PRs
 */
export function useCompareToPRs(workoutId: string) {
  return useQuery({
    queryKey: prKeys.compare(workoutId),
    queryFn: () => compareToPRs(workoutId),
    staleTime: 10 * 60 * 1000, // 10 minutes
    enabled: !!workoutId,
  });
}

/**
 * Hook for detecting PRs in a workout with mutation
 */
export function useDetectPRs() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: detectPRs,
    onSuccess: () => {
      // Invalidate all PR queries to refresh data
      queryClient.invalidateQueries({ queryKey: prKeys.all });
    },
  });
}

/**
 * Hook for PR detection with celebration modal state management
 *
 * This hook combines PR detection with celebration UI state:
 * - Automatically detects PRs when a workout ID is provided
 * - Manages celebration modal visibility
 * - Provides celebration data for the modal
 */
export function usePRCelebration() {
  const [celebrationData, setCelebrationData] = useState<PRCelebrationData | null>(null);
  const [showCelebration, setShowCelebration] = useState(false);

  const detectMutation = useDetectPRs();

  /**
   * Check a workout for PRs and trigger celebration if found
   */
  const checkForPRs = useCallback(async (workoutId: string) => {
    try {
      const result = await detectMutation.mutateAsync({ workoutId });

      if (result.celebrationData) {
        setCelebrationData(result.celebrationData);
        setShowCelebration(true);
      }

      return result;
    } catch (error) {
      console.error('Failed to detect PRs:', error);
      throw error;
    }
  }, [detectMutation]);

  /**
   * Close the celebration modal
   */
  const closeCelebration = useCallback(() => {
    setShowCelebration(false);
    // Keep data briefly for exit animation
    setTimeout(() => {
      setCelebrationData(null);
    }, 300);
  }, []);

  /**
   * Manually trigger a celebration (e.g., from cached data)
   */
  const triggerCelebration = useCallback((data: PRCelebrationData) => {
    setCelebrationData(data);
    setShowCelebration(true);
  }, []);

  return {
    // Detection
    checkForPRs,
    isDetecting: detectMutation.isPending,
    detectionError: detectMutation.error,

    // Celebration state
    showCelebration,
    celebrationData,
    closeCelebration,
    triggerCelebration,
  };
}

/**
 * Hook that automatically checks for PRs after workout analysis
 *
 * Use this hook on workout detail pages to automatically check
 * for PRs after the workout has been analyzed.
 */
export function useAutoDetectPRs(workoutId: string, shouldDetect: boolean = true) {
  const { checkForPRs, showCelebration, celebrationData, closeCelebration } = usePRCelebration();
  const [hasChecked, setHasChecked] = useState(false);

  useEffect(() => {
    if (shouldDetect && workoutId && !hasChecked) {
      checkForPRs(workoutId)
        .then(() => setHasChecked(true))
        .catch(() => setHasChecked(true));
    }
  }, [workoutId, shouldDetect, hasChecked, checkForPRs]);

  // Reset hasChecked when workoutId changes
  useEffect(() => {
    setHasChecked(false);
  }, [workoutId]);

  return {
    showCelebration,
    celebrationData,
    closeCelebration,
    hasChecked,
  };
}

export default usePRCelebration;
