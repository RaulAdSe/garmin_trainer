'use client';

import { useState, useCallback, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getWorkouts,
  getWorkout,
  getWorkoutAnalysis,
  analyzeWorkout,
} from '@/lib/api-client';
import type {
  Workout,
  WorkoutAnalysis,
  WorkoutListFilters,
  PaginatedResponse,
} from '@/lib/types';

// Query keys
export const workoutKeys = {
  all: ['workouts'] as const,
  lists: () => [...workoutKeys.all, 'list'] as const,
  list: (filters?: WorkoutListFilters, page?: number) =>
    [...workoutKeys.lists(), { filters, page }] as const,
  details: () => [...workoutKeys.all, 'detail'] as const,
  detail: (id: string) => [...workoutKeys.details(), id] as const,
  analyses: () => [...workoutKeys.all, 'analysis'] as const,
  analysis: (workoutId: string) => [...workoutKeys.analyses(), workoutId] as const,
};

interface UseWorkoutsOptions {
  page?: number;
  pageSize?: number;
  filters?: WorkoutListFilters;
  sortBy?: 'date' | 'distance' | 'duration';
  sortOrder?: 'asc' | 'desc';
  enabled?: boolean;
}

interface UseWorkoutsReturn {
  workouts: Workout[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => void;
  analyses: Map<string, WorkoutAnalysis>;
  loadingAnalysisId: string | null;
  analyzeWorkout: (workoutId: string, regenerate?: boolean) => Promise<void>;
  filters: WorkoutListFilters;
  setFilters: (filters: WorkoutListFilters) => void;
  setPage: (page: number) => void;
}

export function useWorkouts(options: UseWorkoutsOptions = {}): UseWorkoutsReturn {
  const {
    page: initialPage = 1,
    pageSize = 10,
    filters: initialFilters = {},
    sortBy = 'date',
    sortOrder = 'desc',
    enabled = true,
  } = options;

  const queryClient = useQueryClient();
  const [page, setPage] = useState(initialPage);
  const [filters, setFilters] = useState<WorkoutListFilters>(initialFilters);
  const [analyses, setAnalyses] = useState<Map<string, WorkoutAnalysis>>(new Map());
  const [loadingAnalysisId, setLoadingAnalysisId] = useState<string | null>(null);
  const [fetchedAnalysisIds, setFetchedAnalysisIds] = useState<Set<string>>(new Set());

  // Fetch workouts
  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: workoutKeys.list(filters, page),
    queryFn: () =>
      getWorkouts({
        page,
        pageSize,
        filters,
        sortBy,
        sortOrder,
      }),
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Fetch cached analyses for loaded workouts
  useEffect(() => {
    if (!data?.items?.length) return;

    // Find workouts that we haven't tried to fetch analyses for yet
    const workoutsToFetch = data.items.filter(
      (w) => !analyses.has(w.id) && !fetchedAnalysisIds.has(w.id)
    );

    if (workoutsToFetch.length === 0) return;

    // Mark these as being fetched to avoid duplicate requests
    setFetchedAnalysisIds((prev) => {
      const next = new Set(prev);
      workoutsToFetch.forEach((w) => next.add(w.id));
      return next;
    });

    // Fetch analyses in parallel
    const fetchAnalyses = async () => {
      const results = await Promise.allSettled(
        workoutsToFetch.map((w) => getWorkoutAnalysis(w.id))
      );

      const newAnalyses = new Map<string, WorkoutAnalysis>();
      results.forEach((result, index) => {
        if (result.status === 'fulfilled' && result.value) {
          newAnalyses.set(workoutsToFetch[index].id, result.value);
        }
      });

      if (newAnalyses.size > 0) {
        setAnalyses((prev) => {
          const next = new Map(prev);
          newAnalyses.forEach((analysis, id) => next.set(id, analysis));
          return next;
        });
      }
    };

    fetchAnalyses();
  }, [data?.items, analyses, fetchedAnalysisIds]);

  // Analyze workout mutation
  const analyzeMutation = useMutation({
    mutationFn: async ({
      workoutId,
      regenerate,
    }: {
      workoutId: string;
      regenerate?: boolean;
    }) => {
      console.log('[useWorkouts] Starting analysis for workout:', workoutId);
      try {
        const result = await analyzeWorkout({
          workoutId,
          includeContext: true,
          regenerate,
        });
        console.log('[useWorkouts] Analysis succeeded for workout:', workoutId);
        return result;
      } catch (error) {
        console.error('[useWorkouts] Analysis failed for workout:', workoutId, error);
        throw error;
      }
    },
    onMutate: ({ workoutId }) => {
      setLoadingAnalysisId(workoutId);
    },
    onSuccess: (analysis) => {
      setAnalyses((prev) => {
        const next = new Map(prev);
        next.set(analysis.workoutId, analysis);
        return next;
      });
      // Invalidate the analysis query for this workout
      queryClient.invalidateQueries({
        queryKey: workoutKeys.analysis(analysis.workoutId),
      });
    },
    onError: (error, { workoutId }) => {
      console.error('[useWorkouts] Mutation error for workout:', workoutId, error);
    },
    onSettled: () => {
      setLoadingAnalysisId(null);
    },
  });

  const handleAnalyzeWorkout = useCallback(
    async (workoutId: string, regenerate = false) => {
      if (!workoutId) {
        console.error('[useWorkouts] Cannot analyze: workoutId is empty');
        return;
      }
      console.log('[useWorkouts] handleAnalyzeWorkout called with:', workoutId);
      try {
        await analyzeMutation.mutateAsync({ workoutId, regenerate });
      } catch (error) {
        console.error('[useWorkouts] Analysis mutation failed:', error);
        // Re-throw so React Query can handle it
        throw error;
      }
    },
    [analyzeMutation]
  );

  const handleSetFilters = useCallback((newFilters: WorkoutListFilters) => {
    setFilters(newFilters);
    setPage(1); // Reset to first page when filters change
  }, []);

  return {
    workouts: data?.items ?? [],
    total: data?.total ?? 0,
    page: data?.page ?? page,
    pageSize: data?.pageSize ?? pageSize,
    totalPages: data?.totalPages ?? 0,
    isLoading,
    isError,
    error: error as Error | null,
    refetch,
    analyses,
    loadingAnalysisId,
    analyzeWorkout: handleAnalyzeWorkout,
    filters,
    setFilters: handleSetFilters,
    setPage,
  };
}

// Hook for single workout detail
interface UseWorkoutOptions {
  enabled?: boolean;
}

interface UseWorkoutReturn {
  workout: Workout | null;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useWorkout(
  workoutId: string,
  options: UseWorkoutOptions = {}
): UseWorkoutReturn {
  const { enabled = true } = options;

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: workoutKeys.detail(workoutId),
    queryFn: () => getWorkout(workoutId),
    enabled: enabled && !!workoutId,
    staleTime: 5 * 60 * 1000,
  });

  return {
    workout: data ?? null,
    isLoading,
    isError,
    error: error as Error | null,
    refetch,
  };
}

// Hook for workout analysis
interface UseWorkoutAnalysisReturn {
  analysis: WorkoutAnalysis | null;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => void;
  analyze: (regenerate?: boolean) => Promise<void>;
  isAnalyzing: boolean;
}

export function useWorkoutAnalysis(
  workoutId: string
): UseWorkoutAnalysisReturn {
  const queryClient = useQueryClient();

  // Fetch existing analysis
  const {
    data: existingAnalysis,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: workoutKeys.analysis(workoutId),
    queryFn: () => getWorkoutAnalysis(workoutId),
    enabled: !!workoutId,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });

  // Mutation to generate analysis
  const analyzeMutation = useMutation({
    mutationFn: async (regenerate: boolean = false) => {
      return analyzeWorkout({
        workoutId,
        includeContext: true,
        regenerate,
      });
    },
    onSuccess: (analysis) => {
      queryClient.setQueryData(workoutKeys.analysis(workoutId), analysis);
    },
  });

  const handleAnalyze = useCallback(
    async (regenerate = false) => {
      await analyzeMutation.mutateAsync(regenerate);
    },
    [analyzeMutation]
  );

  return {
    analysis: existingAnalysis ?? null,
    isLoading,
    isError,
    error: error as Error | null,
    refetch,
    analyze: handleAnalyze,
    isAnalyzing: analyzeMutation.isPending,
  };
}

// Hook for infinite scrolling workouts
interface UseInfiniteWorkoutsOptions {
  pageSize?: number;
  filters?: WorkoutListFilters;
  sortBy?: 'date' | 'distance' | 'duration';
  sortOrder?: 'asc' | 'desc';
}

interface UseInfiniteWorkoutsReturn {
  workouts: Workout[];
  isLoading: boolean;
  isLoadingMore: boolean;
  isError: boolean;
  error: Error | null;
  hasMore: boolean;
  loadMore: () => void;
  refetch: () => void;
}

export function useInfiniteWorkouts(
  options: UseInfiniteWorkoutsOptions = {}
): UseInfiniteWorkoutsReturn {
  const {
    pageSize = 10,
    filters = {},
    sortBy = 'date',
    sortOrder = 'desc',
  } = options;

  const [pages, setPages] = useState<PaginatedResponse<Workout>[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  const { isLoading, isError, error, refetch } = useQuery({
    queryKey: workoutKeys.list(filters, currentPage),
    queryFn: async () => {
      const result = await getWorkouts({
        page: currentPage,
        pageSize,
        filters,
        sortBy,
        sortOrder,
      });

      setPages((prev) => {
        // If it's the first page or we're refreshing
        if (currentPage === 1) {
          return [result];
        }
        // Append new page
        const newPages = [...prev];
        newPages[currentPage - 1] = result;
        return newPages;
      });

      return result;
    },
  });

  const workouts = pages.flatMap((page) => page.items);
  const lastPage = pages[pages.length - 1];
  const hasMore = lastPage ? currentPage < lastPage.totalPages : false;

  const loadMore = useCallback(async () => {
    if (!hasMore || isLoadingMore) return;

    setIsLoadingMore(true);
    setCurrentPage((prev) => prev + 1);
    // The query will automatically refetch due to the queryKey change
    setIsLoadingMore(false);
  }, [hasMore, isLoadingMore]);

  const handleRefetch = useCallback(() => {
    setPages([]);
    setCurrentPage(1);
    refetch();
  }, [refetch]);

  return {
    workouts,
    isLoading: isLoading && currentPage === 1,
    isLoadingMore,
    isError,
    error: error as Error | null,
    hasMore,
    loadMore,
    refetch: handleRefetch,
  };
}
