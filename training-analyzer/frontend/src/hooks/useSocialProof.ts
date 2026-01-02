'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getSocialProofStats, type SocialProofStats } from '@/lib/api-client';

/**
 * Query keys for social proof data
 */
export const socialProofKeys = {
  all: ['socialProof'] as const,
  stats: () => [...socialProofKeys.all, 'stats'] as const,
};

/**
 * Hook to fetch and cache social proof statistics.
 *
 * Features:
 * - Caches results for 60 seconds (matching backend cache)
 * - Auto-refetches on window focus (if stale)
 * - Provides loading and error states
 *
 * Returns:
 * - data: SocialProofStats with community counts and percentiles
 * - isLoading: true while fetching
 * - error: any error that occurred
 * - refetch: function to manually refresh data
 */
export function useSocialProof() {
  return useQuery<SocialProofStats>({
    queryKey: socialProofKeys.stats(),
    queryFn: getSocialProofStats,
    staleTime: 60 * 1000, // 60 seconds - matches backend cache
    gcTime: 5 * 60 * 1000, // Keep in cache for 5 minutes
    refetchOnWindowFocus: true,
    refetchOnMount: true,
    retry: 1, // Only retry once - not critical data
  });
}

/**
 * Hook to invalidate social proof cache.
 * Call this after events that might change the user's percentiles
 * (e.g., after completing a workout).
 */
export function useInvalidateSocialProof() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: socialProofKeys.all });
  };
}
