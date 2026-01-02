'use client';

import { useQuery } from '@tanstack/react-query';
import {
  getRecoveryData,
  getSleepDebt,
  getHRVTrend,
  getRecoveryTimeEstimate,
  getRecoveryScore,
} from '@/lib/api-client';
import type {
  RecoveryModuleResponse,
  SleepDebtResponse,
  HRVTrendResponse,
  RecoveryTimeResponse,
  RecoveryScoreResponse,
} from '@/lib/types';

// Query keys for recovery data
export const recoveryKeys = {
  all: ['recovery'] as const,
  data: (options?: RecoveryOptions) => [...recoveryKeys.all, 'data', options] as const,
  sleepDebt: (targetHours?: number, windowDays?: number) =>
    [...recoveryKeys.all, 'sleepDebt', targetHours, windowDays] as const,
  hrvTrend: () => [...recoveryKeys.all, 'hrvTrend'] as const,
  recoveryTime: (workoutId?: string) => [...recoveryKeys.all, 'recoveryTime', workoutId] as const,
  score: () => [...recoveryKeys.all, 'score'] as const,
};

export interface RecoveryOptions {
  targetDate?: string;
  includeSleepDebt?: boolean;
  includeHrvTrend?: boolean;
  includeRecoveryTime?: boolean;
  sleepTargetHours?: number;
}

/**
 * Hook to get complete recovery module data.
 */
export function useRecovery(options?: RecoveryOptions) {
  return useQuery({
    queryKey: recoveryKeys.data(options),
    queryFn: () => getRecoveryData(options),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to get 7-day rolling sleep debt analysis.
 */
export function useSleepDebt(targetHours = 8.0, windowDays = 7) {
  return useQuery({
    queryKey: recoveryKeys.sleepDebt(targetHours, windowDays),
    queryFn: () => getSleepDebt(targetHours, windowDays),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to get HRV trend analysis.
 */
export function useHRVTrend() {
  return useQuery({
    queryKey: recoveryKeys.hrvTrend(),
    queryFn: getHRVTrend,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to get post-workout recovery time estimate.
 */
export function useRecoveryTimeEstimate(workoutId?: string) {
  return useQuery({
    queryKey: recoveryKeys.recoveryTime(workoutId),
    queryFn: () => getRecoveryTimeEstimate(workoutId),
    enabled: !!workoutId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to get just the recovery score for dashboard widgets.
 */
export function useRecoveryScore() {
  return useQuery({
    queryKey: recoveryKeys.score(),
    queryFn: getRecoveryScore,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

