'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  generatePacingPlan,
  calculateWeatherAdjustment,
  getAvailableStrategies,
  getQuickPacingPlan,
} from '@/lib/api-client';
import type {
  PacingPlan,
  GeneratePacingPlanRequest,
  WeatherAdjustment,
  WeatherAdjustmentRequest,
  AvailableStrategiesResponse,
  RaceDistance,
} from '@/lib/types';

// Query keys for race pacing
export const racePacingKeys = {
  all: ['racePacing'] as const,
  strategies: () => [...racePacingKeys.all, 'strategies'] as const,
  plans: () => [...racePacingKeys.all, 'plans'] as const,
  plan: (params: GeneratePacingPlanRequest) => [...racePacingKeys.plans(), params] as const,
  weatherAdjustment: (params: WeatherAdjustmentRequest) =>
    [...racePacingKeys.all, 'weather', params] as const,
};

/**
 * Hook to fetch available pacing strategies and race distances.
 */
export function useAvailableStrategies() {
  return useQuery({
    queryKey: racePacingKeys.strategies(),
    queryFn: getAvailableStrategies,
    staleTime: 1000 * 60 * 60, // 1 hour - strategies don't change often
  });
}

/**
 * Hook to generate a pacing plan.
 * Uses mutation pattern since this is a POST request that generates new data.
 */
export function useGeneratePacingPlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: GeneratePacingPlanRequest) => generatePacingPlan(request),
    onSuccess: (plan, variables) => {
      // Cache the generated plan
      queryClient.setQueryData(racePacingKeys.plan(variables), plan);
    },
  });
}

/**
 * Hook to calculate weather adjustment.
 * Uses mutation pattern since this is a POST request.
 */
export function useCalculateWeatherAdjustment() {
  return useMutation({
    mutationFn: (request: WeatherAdjustmentRequest) => calculateWeatherAdjustment(request),
  });
}

/**
 * Hook to get a quick pacing plan.
 * Uses query pattern for simpler GET-style access.
 */
export function useQuickPacingPlan(
  raceDistance: RaceDistance,
  targetTimeHours: number,
  targetTimeMinutes: number,
  targetTimeSeconds: number = 0,
  customDistanceKm?: number,
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: [
      'racePacing',
      'quickPlan',
      raceDistance,
      targetTimeHours,
      targetTimeMinutes,
      targetTimeSeconds,
      customDistanceKm,
    ],
    queryFn: () =>
      getQuickPacingPlan(
        raceDistance,
        targetTimeHours,
        targetTimeMinutes,
        targetTimeSeconds,
        customDistanceKm
      ),
    enabled: options?.enabled ?? true,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

/**
 * Helper to format pace (seconds per km) to mm:ss string.
 */
export function formatPace(secondsPerKm: number): string {
  const minutes = Math.floor(secondsPerKm / 60);
  const seconds = Math.round(secondsPerKm % 60);
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

/**
 * Helper to format time (seconds) to HH:MM:SS or H:MM:SS string.
 */
export function formatTime(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = Math.round(totalSeconds % 60);

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

/**
 * Helper to parse time string (HH:MM:SS or MM:SS) to seconds.
 */
export function parseTimeString(timeStr: string): number {
  const parts = timeStr.split(':').map(Number);
  if (parts.length === 3) {
    const [hours, minutes, seconds] = parts;
    return hours * 3600 + minutes * 60 + seconds;
  } else if (parts.length === 2) {
    const [minutes, seconds] = parts;
    return minutes * 60 + seconds;
  }
  throw new Error(`Invalid time format: ${timeStr}`);
}

/**
 * Helper to get time components from total seconds.
 */
export function getTimeComponents(totalSeconds: number): {
  hours: number;
  minutes: number;
  seconds: number;
} {
  return {
    hours: Math.floor(totalSeconds / 3600),
    minutes: Math.floor((totalSeconds % 3600) / 60),
    seconds: Math.round(totalSeconds % 60),
  };
}

// Re-export types for convenience
export type {
  PacingPlan,
  GeneratePacingPlanRequest,
  WeatherAdjustment,
  WeatherAdjustmentRequest,
  AvailableStrategiesResponse,
};
