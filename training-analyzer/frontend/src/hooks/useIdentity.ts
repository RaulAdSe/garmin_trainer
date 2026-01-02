'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// =============================================================================
// Types
// =============================================================================

export interface IdentityStatement {
  id: number;
  userId: string;
  statement: string;
  createdAt: string;
  lastReinforcedAt: string;
  reinforcementCount: number;
}

export interface IdentityTemplate {
  id: string;
  statement: string;
  description: string;
}

export interface ReinforcementCheck {
  shouldShowReinforcement: boolean;
  statement: IdentityStatement | null;
}

// =============================================================================
// Query Keys
// =============================================================================

export const identityKeys = {
  all: ['identity'] as const,
  statement: () => [...identityKeys.all, 'statement'] as const,
  templates: () => [...identityKeys.all, 'templates'] as const,
  reinforcement: () => [...identityKeys.all, 'reinforcement'] as const,
};

// =============================================================================
// API Functions
// =============================================================================

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

async function fetchIdentityStatement(): Promise<IdentityStatement | null> {
  const response = await fetch(`${API_BASE}/api/v1/emotional/identity`, {
    credentials: 'include',
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Unauthorized');
    }
    throw new Error('Failed to fetch identity statement');
  }

  const data = await response.json();
  return data;
}

async function fetchIdentityTemplates(): Promise<IdentityTemplate[]> {
  const response = await fetch(`${API_BASE}/api/v1/emotional/identity/templates`, {
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error('Failed to fetch identity templates');
  }

  const data = await response.json();
  return data.templates;
}

async function createIdentityStatement(
  statement: string
): Promise<IdentityStatement> {
  const response = await fetch(`${API_BASE}/api/v1/emotional/identity`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({ statement }),
  });

  if (!response.ok) {
    throw new Error('Failed to create identity statement');
  }

  return response.json();
}

async function reinforceIdentityStatement(): Promise<IdentityStatement> {
  const response = await fetch(`${API_BASE}/api/v1/emotional/identity/reinforce`, {
    method: 'POST',
    credentials: 'include',
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('No identity statement found');
    }
    throw new Error('Failed to reinforce identity statement');
  }

  return response.json();
}

async function checkReinforcement(
  daysThreshold: number = 7
): Promise<ReinforcementCheck> {
  const response = await fetch(
    `${API_BASE}/api/v1/emotional/identity/check-reinforcement?days_threshold=${daysThreshold}`,
    {
      credentials: 'include',
    }
  );

  if (!response.ok) {
    throw new Error('Failed to check reinforcement');
  }

  return response.json();
}

async function deleteIdentityStatement(): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/emotional/identity`, {
    method: 'DELETE',
    credentials: 'include',
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('No identity statement found');
    }
    throw new Error('Failed to delete identity statement');
  }
}

// =============================================================================
// Hooks
// =============================================================================

/**
 * Hook to fetch the user's identity statement
 */
export function useIdentityStatement() {
  return useQuery({
    queryKey: identityKeys.statement(),
    queryFn: fetchIdentityStatement,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: (failureCount, error) => {
      // Don't retry on 401
      if (error instanceof Error && error.message === 'Unauthorized') {
        return false;
      }
      return failureCount < 2;
    },
  });
}

/**
 * Hook to fetch identity statement templates
 */
export function useIdentityTemplates() {
  return useQuery({
    queryKey: identityKeys.templates(),
    queryFn: fetchIdentityTemplates,
    staleTime: 30 * 60 * 1000, // 30 minutes (templates rarely change)
    gcTime: 60 * 60 * 1000, // 1 hour
  });
}

/**
 * Hook to create or update identity statement
 */
export function useCreateIdentityStatement() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createIdentityStatement,
    onSuccess: (data) => {
      // Update the statement cache
      queryClient.setQueryData(identityKeys.statement(), data);
      // Invalidate reinforcement check
      queryClient.invalidateQueries({ queryKey: identityKeys.reinforcement() });
    },
  });
}

/**
 * Hook to reinforce identity statement
 */
export function useReinforceIdentity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: reinforceIdentityStatement,
    onSuccess: (data) => {
      // Update the statement cache with new reinforcement count
      queryClient.setQueryData(identityKeys.statement(), data);
      // Invalidate reinforcement check
      queryClient.invalidateQueries({ queryKey: identityKeys.reinforcement() });
    },
  });
}

/**
 * Hook to check if reinforcement reminder should be shown
 */
export function useReinforcementCheck(daysThreshold: number = 7) {
  return useQuery({
    queryKey: [...identityKeys.reinforcement(), daysThreshold],
    queryFn: () => checkReinforcement(daysThreshold),
    staleTime: 60 * 60 * 1000, // 1 hour (don't check too often)
    gcTime: 2 * 60 * 60 * 1000, // 2 hours
    retry: false,
  });
}

/**
 * Hook to delete identity statement
 */
export function useDeleteIdentityStatement() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteIdentityStatement,
    onSuccess: () => {
      // Clear the statement cache
      queryClient.setQueryData(identityKeys.statement(), null);
      // Invalidate reinforcement check
      queryClient.invalidateQueries({ queryKey: identityKeys.reinforcement() });
    },
  });
}

/**
 * Combined hook for identity management
 *
 * Provides all identity-related functionality in one hook
 */
export function useIdentity() {
  const statementQuery = useIdentityStatement();
  const templatesQuery = useIdentityTemplates();
  const reinforcementQuery = useReinforcementCheck();
  const createMutation = useCreateIdentityStatement();
  const reinforceMutation = useReinforceIdentity();
  const deleteMutation = useDeleteIdentityStatement();

  return {
    // Data
    statement: statementQuery.data,
    templates: templatesQuery.data || [],
    reinforcementCheck: reinforcementQuery.data,

    // Loading states
    isLoadingStatement: statementQuery.isLoading,
    isLoadingTemplates: templatesQuery.isLoading,
    isLoadingReinforcement: reinforcementQuery.isLoading,

    // Error states
    statementError: statementQuery.error,
    templatesError: templatesQuery.error,

    // Mutations
    createStatement: createMutation.mutate,
    createStatementAsync: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    createError: createMutation.error,

    reinforce: reinforceMutation.mutate,
    reinforceAsync: reinforceMutation.mutateAsync,
    isReinforcing: reinforceMutation.isPending,

    deleteStatement: deleteMutation.mutate,
    deleteStatementAsync: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,

    // Computed
    hasStatement: !!statementQuery.data,
    shouldShowReinforcement:
      reinforcementQuery.data?.shouldShowReinforcement ?? false,
  };
}
