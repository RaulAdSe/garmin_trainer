'use client';

import { useQuery } from '@tanstack/react-query';
import {
  getTimingAnalysis,
  getTSBOptimalRange,
  getPeakFitnessPrediction,
  getPerformanceCorrelations,
  getPatternSummary,
} from '@/lib/api-client';
import type {
  TimingAnalysis,
  TSBOptimalRange,
  FitnessPrediction,
  PerformanceCorrelations,
  PatternSummary,
} from '@/types/patterns';

// Query keys for pattern recognition data
export const patternKeys = {
  all: ['patterns'] as const,
  timing: (days: number) => [...patternKeys.all, 'timing', days] as const,
  tsbOptimal: (days: number) => [...patternKeys.all, 'tsbOptimal', days] as const,
  fitnessPrediction: (targetDate?: string, horizonDays?: number) =>
    [...patternKeys.all, 'fitnessPrediction', targetDate, horizonDays] as const,
  correlations: (days: number) => [...patternKeys.all, 'correlations', days] as const,
  summary: (days: number) => [...patternKeys.all, 'summary', days] as const,
};

/**
 * Hook to get timing pattern analysis (best times/days to train).
 */
export function useTimingAnalysis(days = 90) {
  return useQuery({
    queryKey: patternKeys.timing(days),
    queryFn: () => getTimingAnalysis(days),
    staleTime: 10 * 60 * 1000, // 10 minutes - patterns don't change frequently
  });
}

/**
 * Hook to get optimal TSB range for peak performance.
 */
export function useTSBOptimalRange(days = 180) {
  return useQuery({
    queryKey: patternKeys.tsbOptimal(days),
    queryFn: () => getTSBOptimalRange(days),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook to get peak fitness prediction.
 */
export function usePeakFitnessPrediction(targetDate?: string, horizonDays = 90) {
  return useQuery({
    queryKey: patternKeys.fitnessPrediction(targetDate, horizonDays),
    queryFn: () => getPeakFitnessPrediction(targetDate, horizonDays),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook to get performance correlations analysis.
 */
export function usePerformanceCorrelations(days = 180) {
  return useQuery({
    queryKey: patternKeys.correlations(days),
    queryFn: () => getPerformanceCorrelations(days),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook to get combined pattern analysis summary.
 */
export function usePatternSummary(days = 90) {
  return useQuery({
    queryKey: patternKeys.summary(days),
    queryFn: () => getPatternSummary(days),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

