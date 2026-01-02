'use client';

import { useQuery } from '@tanstack/react-query';
import {
  getCurrentEconomy,
  getEconomyTrend,
  getCardiacDrift,
  getPaceZonesEconomy,
} from '@/lib/api-client';

// Query keys for running economy data
export const economyKeys = {
  all: ['economy'] as const,
  current: () => [...economyKeys.all, 'current'] as const,
  trend: (days: number) => [...economyKeys.all, 'trend', days] as const,
  cardiacDrift: (workoutId: string) => [...economyKeys.all, 'cardiacDrift', workoutId] as const,
  paceZones: (days: number) => [...economyKeys.all, 'paceZones', days] as const,
};

/**
 * Hook to get the most recent running economy metrics.
 */
export function useCurrentEconomy() {
  return useQuery({
    queryKey: economyKeys.current(),
    queryFn: getCurrentEconomy,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to get running economy trend over time.
 */
export function useEconomyTrend(days = 90) {
  return useQuery({
    queryKey: economyKeys.trend(days),
    queryFn: () => getEconomyTrend(days),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to get cardiac drift analysis for a specific workout.
 */
export function useCardiacDrift(workoutId: string) {
  return useQuery({
    queryKey: economyKeys.cardiacDrift(workoutId),
    queryFn: () => getCardiacDrift(workoutId),
    enabled: !!workoutId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to get economy metrics by pace zone.
 */
export function usePaceZonesEconomy(days = 90) {
  return useQuery({
    queryKey: economyKeys.paceZones(days),
    queryFn: () => getPaceZonesEconomy(days),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

