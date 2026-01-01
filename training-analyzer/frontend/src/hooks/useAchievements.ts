'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getAchievements,
  getRecentAchievements,
  getUserProgress,
  checkAchievements
} from '@/lib/api-client';

export const achievementKeys = {
  all: ['achievements'] as const,
  list: () => [...achievementKeys.all, 'list'] as const,
  recent: () => [...achievementKeys.all, 'recent'] as const,
  progress: () => [...achievementKeys.all, 'progress'] as const,
};

export function useAchievements() {
  return useQuery({
    queryKey: achievementKeys.list(),
    queryFn: getAchievements,
    staleTime: 5 * 60 * 1000,
  });
}

export function useRecentAchievements() {
  return useQuery({
    queryKey: achievementKeys.recent(),
    queryFn: getRecentAchievements,
    staleTime: 60 * 1000,
  });
}

export function useUserProgress() {
  return useQuery({
    queryKey: achievementKeys.progress(),
    queryFn: getUserProgress,
    staleTime: 60 * 1000,
  });
}

export function useCheckAchievements() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: checkAchievements,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: achievementKeys.all });
    },
  });
}
