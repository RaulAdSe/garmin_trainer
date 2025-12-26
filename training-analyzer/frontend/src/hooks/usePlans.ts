'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useCallback } from 'react';
import {
  getPlans,
  getPlan,
  getPlanWeek,
  createPlan,
  generatePlan,
  generatePlanStream,
  updatePlan,
  deletePlan,
  activatePlan,
  pausePlan,
  updateSession,
  completeSession,
  skipSession,
  getActivePlan,
  adaptPlan,
} from '@/lib/api-client';
import type {
  TrainingPlan,
  PlanSummary,
  TrainingWeek,
  TrainingSession,
  CreatePlanRequest,
  GeneratePlanRequest,
  UpdatePlanRequest,
  UpdateSessionRequest,
  PlanListRequest,
  PaginatedResponse,
} from '@/lib/types';

// Query keys
export const planKeys = {
  all: ['plans'] as const,
  lists: () => [...planKeys.all, 'list'] as const,
  list: (filters: PlanListRequest) => [...planKeys.lists(), filters] as const,
  details: () => [...planKeys.all, 'detail'] as const,
  detail: (id: string) => [...planKeys.details(), id] as const,
  weeks: (planId: string) => [...planKeys.detail(planId), 'weeks'] as const,
  week: (planId: string, weekNumber: number) =>
    [...planKeys.weeks(planId), weekNumber] as const,
  active: () => [...planKeys.all, 'active'] as const,
};

// Hook to fetch list of plans
export function usePlansList(request: PlanListRequest = {}) {
  return useQuery({
    queryKey: planKeys.list(request),
    queryFn: () => getPlans(request),
  });
}

// Hook to fetch a single plan
export function usePlan(planId: string | undefined) {
  return useQuery({
    queryKey: planKeys.detail(planId!),
    queryFn: () => getPlan(planId!),
    enabled: !!planId,
  });
}

// Hook to fetch a specific week
export function usePlanWeek(planId: string | undefined, weekNumber: number) {
  return useQuery({
    queryKey: planKeys.week(planId!, weekNumber),
    queryFn: () => getPlanWeek(planId!, weekNumber),
    enabled: !!planId,
  });
}

// Hook to fetch active plan
export function useActivePlan() {
  return useQuery({
    queryKey: planKeys.active(),
    queryFn: getActivePlan,
  });
}

// Hook to create a plan
export function useCreatePlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CreatePlanRequest) => createPlan(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: planKeys.lists() });
    },
  });
}

// Hook to generate a plan with AI
export function useGeneratePlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: GeneratePlanRequest) => generatePlan(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: planKeys.lists() });
    },
  });
}

// Hook for streaming plan generation
export interface GenerationProgress {
  phase: string;
  message: string;
  percentage: number;
}

export function useGeneratePlanStream() {
  const queryClient = useQueryClient();
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState<GenerationProgress | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [generatedPlan, setGeneratedPlan] = useState<TrainingPlan | null>(null);
  const [abortFn, setAbortFn] = useState<(() => void) | null>(null);

  const generate = useCallback(
    (request: GeneratePlanRequest) => {
      setIsGenerating(true);
      setProgress(null);
      setError(null);
      setGeneratedPlan(null);

      const abort = generatePlanStream(
        request,
        (progressUpdate) => {
          setProgress(progressUpdate);
        },
        (plan) => {
          setGeneratedPlan(plan);
          setIsGenerating(false);
          queryClient.invalidateQueries({ queryKey: planKeys.lists() });
        },
        (err) => {
          setError(err);
          setIsGenerating(false);
        }
      );

      setAbortFn(() => abort);
    },
    [queryClient]
  );

  const cancel = useCallback(() => {
    if (abortFn) {
      abortFn();
      setIsGenerating(false);
    }
  }, [abortFn]);

  const reset = useCallback(() => {
    setIsGenerating(false);
    setProgress(null);
    setError(null);
    setGeneratedPlan(null);
    setAbortFn(null);
  }, []);

  return {
    generate,
    cancel,
    reset,
    isGenerating,
    progress,
    error,
    generatedPlan,
  };
}

// Hook to update a plan
export function useUpdatePlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      planId,
      request,
    }: {
      planId: string;
      request: UpdatePlanRequest;
    }) => updatePlan(planId, request),
    onSuccess: (updatedPlan) => {
      queryClient.setQueryData(planKeys.detail(updatedPlan.id), updatedPlan);
      queryClient.invalidateQueries({ queryKey: planKeys.lists() });
    },
  });
}

// Hook to delete a plan
export function useDeletePlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (planId: string) => deletePlan(planId),
    onSuccess: (_, planId) => {
      queryClient.removeQueries({ queryKey: planKeys.detail(planId) });
      queryClient.invalidateQueries({ queryKey: planKeys.lists() });
    },
  });
}

// Hook to activate a plan
export function useActivatePlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (planId: string) => activatePlan(planId),
    onSuccess: (updatedPlan) => {
      queryClient.setQueryData(planKeys.detail(updatedPlan.id), updatedPlan);
      queryClient.invalidateQueries({ queryKey: planKeys.lists() });
      queryClient.invalidateQueries({ queryKey: planKeys.active() });
    },
  });
}

// Hook to pause a plan
export function usePausePlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (planId: string) => pausePlan(planId),
    onSuccess: (updatedPlan) => {
      queryClient.setQueryData(planKeys.detail(updatedPlan.id), updatedPlan);
      queryClient.invalidateQueries({ queryKey: planKeys.lists() });
      queryClient.invalidateQueries({ queryKey: planKeys.active() });
    },
  });
}

// Hook to update a session
export function useUpdateSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      planId,
      sessionId,
      request,
    }: {
      planId: string;
      sessionId: string;
      request: UpdateSessionRequest;
    }) => updateSession(planId, sessionId, request),
    onSuccess: (_, { planId }) => {
      queryClient.invalidateQueries({ queryKey: planKeys.detail(planId) });
      queryClient.invalidateQueries({ queryKey: planKeys.weeks(planId) });
    },
  });
}

// Hook to complete a session
export function useCompleteSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      planId,
      sessionId,
      workoutId,
    }: {
      planId: string;
      sessionId: string;
      workoutId?: string;
    }) => completeSession(planId, sessionId, workoutId),
    onSuccess: (_, { planId }) => {
      queryClient.invalidateQueries({ queryKey: planKeys.detail(planId) });
      queryClient.invalidateQueries({ queryKey: planKeys.weeks(planId) });
    },
  });
}

// Hook to skip a session
export function useSkipSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      planId,
      sessionId,
      notes,
    }: {
      planId: string;
      sessionId: string;
      notes?: string;
    }) => skipSession(planId, sessionId, notes),
    onSuccess: (_, { planId }) => {
      queryClient.invalidateQueries({ queryKey: planKeys.detail(planId) });
      queryClient.invalidateQueries({ queryKey: planKeys.weeks(planId) });
    },
  });
}

// Hook to adapt a plan
export function useAdaptPlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ planId, reason }: { planId: string; reason?: string }) =>
      adaptPlan(planId, reason),
    onSuccess: (updatedPlan) => {
      queryClient.setQueryData(planKeys.detail(updatedPlan.id), updatedPlan);
      queryClient.invalidateQueries({ queryKey: planKeys.lists() });
    },
  });
}
