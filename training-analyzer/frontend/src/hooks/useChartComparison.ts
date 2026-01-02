'use client';

import { useState, useCallback, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getComparableWorkouts,
  getNormalizedData,
  compareWorkouts,
} from '@/lib/api-client';
import type {
  ComparisonTarget,
  NormalizedTimeSeries,
  ComparisonStats,
  WorkoutComparisonData,
  NormalizationMode,
} from '@/types/comparison';

// Query keys for comparison data
export const comparisonKeys = {
  all: ['comparison'] as const,
  comparable: (activityId: string) => [...comparisonKeys.all, 'comparable', activityId] as const,
  normalized: (activityId: string, mode: NormalizationMode) =>
    [...comparisonKeys.all, 'normalized', activityId, mode] as const,
  compare: (primaryId: string, comparisonId: string) =>
    [...comparisonKeys.all, 'compare', primaryId, comparisonId] as const,
};

export interface UseChartComparisonOptions {
  activityId: string;
  enabled?: boolean;
}

export interface UseChartComparisonReturn {
  // Comparison state
  isComparisonEnabled: boolean;
  selectedComparisonId: string | null;
  normalizationMode: NormalizationMode;

  // Data
  comparableWorkouts: ComparisonTarget[];
  quickSelections: ComparisonTarget[];
  comparisonData: WorkoutComparisonData | null;
  stats: ComparisonStats | null;

  // Loading states
  isLoadingComparable: boolean;
  isLoadingComparison: boolean;
  isComparing: boolean;

  // Actions
  enableComparison: () => void;
  disableComparison: () => void;
  selectComparison: (workoutId: string) => void;
  clearComparison: () => void;
  setNormalizationMode: (mode: NormalizationMode) => void;

  // Errors
  error: Error | null;
}

/**
 * Hook for managing chart comparison state and data.
 *
 * Usage:
 * ```tsx
 * const {
 *   isComparisonEnabled,
 *   comparableWorkouts,
 *   selectComparison,
 *   comparisonData,
 * } = useChartComparison({ activityId: workout.id });
 * ```
 */
export function useChartComparison(
  options: UseChartComparisonOptions
): UseChartComparisonReturn {
  const { activityId, enabled = true } = options;

  const queryClient = useQueryClient();

  // Local state
  const [isComparisonEnabled, setIsComparisonEnabled] = useState(false);
  const [selectedComparisonId, setSelectedComparisonId] = useState<string | null>(null);
  const [normalizationMode, setNormalizationMode] = useState<NormalizationMode>('percentage');

  // Fetch comparable workouts
  const {
    data: comparableData,
    isLoading: isLoadingComparable,
    error: comparableError,
  } = useQuery({
    queryKey: comparisonKeys.comparable(activityId),
    queryFn: () => getComparableWorkouts(activityId),
    enabled: enabled && isComparisonEnabled,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });

  // Fetch comparison data when a workout is selected
  const {
    data: comparisonData,
    isLoading: isLoadingComparison,
    error: comparisonError,
  } = useQuery({
    queryKey: comparisonKeys.compare(activityId, selectedComparisonId || ''),
    queryFn: () =>
      compareWorkouts(activityId, selectedComparisonId!, normalizationMode),
    enabled: enabled && isComparisonEnabled && !!selectedComparisonId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Actions
  const enableComparison = useCallback(() => {
    setIsComparisonEnabled(true);
  }, []);

  const disableComparison = useCallback(() => {
    setIsComparisonEnabled(false);
    setSelectedComparisonId(null);
  }, []);

  const selectComparison = useCallback((workoutId: string) => {
    setSelectedComparisonId(workoutId);
  }, []);

  const clearComparison = useCallback(() => {
    setSelectedComparisonId(null);
  }, []);

  const handleSetNormalizationMode = useCallback((mode: NormalizationMode) => {
    setNormalizationMode(mode);
    // Invalidate comparison query to refetch with new mode
    if (selectedComparisonId) {
      queryClient.invalidateQueries({
        queryKey: comparisonKeys.compare(activityId, selectedComparisonId),
      });
    }
  }, [activityId, selectedComparisonId, queryClient]);

  // Derived data
  const comparableWorkouts = useMemo(() => {
    return comparableData?.targets ?? [];
  }, [comparableData]);

  const quickSelections = useMemo(() => {
    return comparableData?.quick_selections ?? [];
  }, [comparableData]);

  const stats = useMemo(() => {
    return comparisonData?.stats ?? null;
  }, [comparisonData]);

  // Combine errors
  const error = comparableError ?? comparisonError ?? null;

  return {
    isComparisonEnabled,
    selectedComparisonId,
    normalizationMode,
    comparableWorkouts,
    quickSelections,
    comparisonData: comparisonData ?? null,
    stats,
    isLoadingComparable,
    isLoadingComparison,
    isComparing: isLoadingComparison,
    enableComparison,
    disableComparison,
    selectComparison,
    clearComparison,
    setNormalizationMode: handleSetNormalizationMode,
    error: error as Error | null,
  };
}

/**
 * Hook to get quick selection label for display.
 */
export function useQuickSelectionLabel(type: string | null | undefined): string {
  if (!type) return '';

  const labels: Record<string, string> = {
    last_similar: 'Last Similar',
    best_pace: 'Best Pace',
    best_5k: 'Best 5K',
    best_10k: 'Best 10K',
    best_half_marathon: 'Best Half Marathon',
    best_marathon: 'Best Marathon',
  };

  return labels[type] ?? type;
}

export default useChartComparison;
