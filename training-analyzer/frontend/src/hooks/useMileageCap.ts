'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getMileageCap,
  checkPlannedRun,
  getWeeklyComparison,
  getTenPercentRuleInfo,
} from '@/lib/api-client';
import type {
  MileageCapData,
  PlannedRunCheckData,
  WeeklyComparisonData,
  TenPercentRuleInfo,
} from '@/lib/types';

// Query keys for cache management
export const mileageCapKeys = {
  all: ['mileageCap'] as const,
  cap: () => [...mileageCapKeys.all, 'cap'] as const,
  capByDate: (date?: string) => [...mileageCapKeys.cap(), date] as const,
  comparison: () => [...mileageCapKeys.all, 'comparison'] as const,
  comparisonByDate: (date?: string) => [...mileageCapKeys.comparison(), date] as const,
  info: () => [...mileageCapKeys.all, 'info'] as const,
};

/**
 * Hook to fetch the current mileage cap status based on the 10% rule.
 *
 * The 10% rule recommends not increasing weekly mileage by more than
 * 10% from one week to the next to prevent overuse injuries.
 *
 * @param targetDate - Optional date to calculate cap for (defaults to today)
 * @param options - Query options
 */
export function useMileageCap(targetDate?: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: mileageCapKeys.capByDate(targetDate),
    queryFn: () => getMileageCap(targetDate),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: options?.enabled !== false,
  });
}

/**
 * Hook to check if a planned run would exceed the weekly mileage cap.
 *
 * Returns a mutation function that can be called with the planned distance.
 * Use this to verify a planned run is safe before heading out.
 */
export function useCheckPlannedRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ plannedKm, targetDate }: { plannedKm: number; targetDate?: string }) =>
      checkPlannedRun(plannedKm, targetDate),
    onSuccess: () => {
      // Optionally invalidate cap data after checking
      // (not strictly necessary but keeps data fresh)
    },
  });
}

/**
 * Hook to fetch week-over-week mileage comparison.
 *
 * Shows how the current week compares to the previous week,
 * including percentage change and detailed breakdown.
 *
 * @param targetDate - Optional date to calculate comparison for
 * @param options - Query options
 */
export function useWeeklyComparison(targetDate?: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: mileageCapKeys.comparisonByDate(targetDate),
    queryFn: () => getWeeklyComparison(targetDate),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: options?.enabled !== false,
  });
}

/**
 * Hook to fetch educational information about the 10% rule.
 *
 * Returns title, description, benefits, and tips about
 * the 10% rule for injury prevention.
 */
export function useTenPercentRuleInfo() {
  return useQuery({
    queryKey: mileageCapKeys.info(),
    queryFn: getTenPercentRuleInfo,
    staleTime: 24 * 60 * 60 * 1000, // 24 hours - rarely changes
  });
}

/**
 * Combined hook for all mileage cap functionality.
 *
 * Provides:
 * - Current cap status
 * - Weekly comparison
 * - Ability to check planned runs
 * - Refresh functionality
 *
 * @param targetDate - Optional date to use for calculations
 */
export function useMileageCapComplete(targetDate?: string) {
  const queryClient = useQueryClient();

  // Fetch cap data
  const capQuery = useMileageCap(targetDate);

  // Fetch comparison data
  const comparisonQuery = useWeeklyComparison(targetDate);

  // Check planned run mutation
  const checkRunMutation = useCheckPlannedRun();

  // Refresh function to invalidate all mileage cap queries
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: mileageCapKeys.all });
  };

  return {
    // Cap status
    capData: capQuery.data,
    isCapLoading: capQuery.isLoading,
    capError: capQuery.error,

    // Comparison
    comparisonData: comparisonQuery.data,
    isComparisonLoading: comparisonQuery.isLoading,
    comparisonError: comparisonQuery.error,

    // Check planned run
    checkPlannedRun: checkRunMutation.mutateAsync,
    isCheckingRun: checkRunMutation.isPending,
    checkResult: checkRunMutation.data,
    checkError: checkRunMutation.error,
    resetCheck: checkRunMutation.reset,

    // Combined loading state
    isLoading: capQuery.isLoading || comparisonQuery.isLoading,

    // Refresh
    refresh,
  };
}

// Type exports for convenience
export type { MileageCapData, PlannedRunCheckData, WeeklyComparisonData, TenPercentRuleInfo };
