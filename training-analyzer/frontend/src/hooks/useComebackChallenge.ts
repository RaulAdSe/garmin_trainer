'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getComebackChallenge,
  recordComebackWorkout,
  triggerComebackChallenge,
  getComebackChallengeHistory,
  cancelComebackChallenge,
} from '@/lib/api-client';

/**
 * Type definitions for the Comeback Challenge system.
 */
export interface ComebackChallenge {
  id: string;
  userId: string;
  triggeredAt: string;
  previousStreak: number;
  status: 'active' | 'completed' | 'expired' | 'cancelled';
  day1CompletedAt: string | null;
  day2CompletedAt: string | null;
  day3CompletedAt: string | null;
  xpMultiplier: number;
  bonusXpEarned: number;
  expiresAt: string | null;
  createdAt: string | null;
  daysCompleted: number;
  isComplete: boolean;
  isActive: boolean;
  nextDayToComplete: number | null;
}

export interface RecordWorkoutResponse {
  success: boolean;
  challenge: ComebackChallenge | null;
  bonusXpEarned: number;
  totalXpEarned: number;
  challengeCompleted: boolean;
  message: string;
}

export interface ChallengeHistoryResponse {
  challenges: ComebackChallenge[];
  total: number;
}

/**
 * Query keys for comeback challenge data.
 */
export const comebackChallengeKeys = {
  all: ['comebackChallenge'] as const,
  active: () => [...comebackChallengeKeys.all, 'active'] as const,
  history: () => [...comebackChallengeKeys.all, 'history'] as const,
};

/**
 * Hook to fetch the active comeback challenge for the current user.
 */
export function useComebackChallenge() {
  return useQuery({
    queryKey: comebackChallengeKeys.active(),
    queryFn: getComebackChallenge,
    staleTime: 60 * 1000, // 1 minute
    refetchOnWindowFocus: true,
  });
}

/**
 * Hook to record a workout during an active comeback challenge.
 * Applies XP multiplier and updates challenge progress.
 */
export function useRecordComebackWorkout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      workoutId,
      baseXp,
    }: {
      workoutId: string;
      baseXp?: number;
    }) => recordComebackWorkout(workoutId, baseXp),
    onSuccess: () => {
      // Invalidate comeback challenge queries to refresh data
      queryClient.invalidateQueries({
        queryKey: comebackChallengeKeys.all,
      });
      // Also invalidate achievements/progress since XP was earned
      queryClient.invalidateQueries({
        queryKey: ['achievements'],
      });
    },
  });
}

/**
 * Hook to trigger a new comeback challenge.
 * Typically called when a streak breaks.
 */
export function useTriggerComebackChallenge() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (previousStreak: number) =>
      triggerComebackChallenge(previousStreak),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: comebackChallengeKeys.all,
      });
    },
  });
}

/**
 * Hook to fetch comeback challenge history.
 */
export function useComebackChallengeHistory(limit: number = 10) {
  return useQuery({
    queryKey: [...comebackChallengeKeys.history(), limit],
    queryFn: () => getComebackChallengeHistory(limit),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to cancel an active comeback challenge.
 */
export function useCancelComebackChallenge() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (challengeId: string) => cancelComebackChallenge(challengeId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: comebackChallengeKeys.all,
      });
    },
  });
}

export default useComebackChallenge;
