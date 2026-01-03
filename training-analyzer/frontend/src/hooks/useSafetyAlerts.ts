'use client';

import { useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getSafetyAlerts,
  acknowledgeAlert,
  dismissAlert,
  getLoadAnalysis,
  type GetSafetyAlertsOptions,
} from '@/lib/api-client';
import type {
  SafetyAlert,
  SafetyAlertsResponse,
  LoadAnalysisData,
  AlertSeverity,
} from '@/lib/types';

// Query keys for safety alerts
export const safetyKeys = {
  all: ['safety'] as const,
  alerts: () => [...safetyKeys.all, 'alerts'] as const,
  alertsList: (options?: GetSafetyAlertsOptions) =>
    [...safetyKeys.alerts(), options] as const,
  loadAnalysis: () => [...safetyKeys.all, 'load-analysis'] as const,
};

// ============================================
// useSafetyAlerts Hook
// ============================================

export interface UseSafetyAlertsOptions {
  status?: 'active' | 'acknowledged' | 'resolved' | 'dismissed';
  severity?: AlertSeverity;
  days?: number;
  enabled?: boolean;
  refetchInterval?: number;
}

export interface UseSafetyAlertsReturn {
  alerts: SafetyAlert[];
  activeCount: number;
  criticalCount: number;
  total: number;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => void;
  acknowledge: (alertId: string) => Promise<void>;
  dismiss: (alertId: string) => Promise<void>;
  isAcknowledging: boolean;
  isDismissing: boolean;
  hasCriticalAlerts: boolean;
  hasActiveAlerts: boolean;
}

/**
 * Hook for fetching and managing safety alerts.
 *
 * Provides ACWR spike detection, monotony, and strain alerts
 * with auto-refresh capability.
 */
export function useSafetyAlerts(
  options: UseSafetyAlertsOptions = {}
): UseSafetyAlertsReturn {
  const {
    status,
    severity,
    days = 14,
    enabled = true,
    refetchInterval,
  } = options;

  const queryClient = useQueryClient();

  // Fetch alerts
  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: safetyKeys.alertsList({ status, severity, days }),
    queryFn: () => getSafetyAlerts({ status, severity, days }),
    enabled,
    staleTime: 2 * 60 * 1000, // 2 minutes
    refetchInterval: refetchInterval || undefined,
    refetchOnWindowFocus: true,
  });

  // Acknowledge mutation
  const acknowledgeMutation = useMutation({
    mutationFn: (alertId: string) => acknowledgeAlert(alertId),
    onSuccess: (_, alertId) => {
      // Optimistically update the cache
      queryClient.setQueryData<SafetyAlertsResponse>(
        safetyKeys.alertsList({ status, severity, days }),
        (old) => {
          if (!old) return old;
          return {
            ...old,
            alerts: old.alerts.map((a) =>
              a.id === alertId
                ? { ...a, status: 'acknowledged' as const, acknowledgedAt: new Date().toISOString() }
                : a
            ),
            activeCount: Math.max(0, old.activeCount - 1),
          };
        }
      );
      // Invalidate to refetch fresh data
      queryClient.invalidateQueries({ queryKey: safetyKeys.alerts() });
    },
  });

  // Dismiss mutation
  const dismissMutation = useMutation({
    mutationFn: (alertId: string) => dismissAlert(alertId),
    onSuccess: (_, alertId) => {
      // Optimistically update the cache
      queryClient.setQueryData<SafetyAlertsResponse>(
        safetyKeys.alertsList({ status, severity, days }),
        (old) => {
          if (!old) return old;
          return {
            ...old,
            alerts: old.alerts.map((a) =>
              a.id === alertId
                ? { ...a, status: 'dismissed' as const }
                : a
            ),
            activeCount: Math.max(0, old.activeCount - 1),
          };
        }
      );
      // Invalidate to refetch fresh data
      queryClient.invalidateQueries({ queryKey: safetyKeys.alerts() });
    },
  });

  const handleAcknowledge = useCallback(
    async (alertId: string) => {
      await acknowledgeMutation.mutateAsync(alertId);
    },
    [acknowledgeMutation]
  );

  const handleDismiss = useCallback(
    async (alertId: string) => {
      await dismissMutation.mutateAsync(alertId);
    },
    [dismissMutation]
  );

  const alerts = data?.alerts ?? [];
  const activeCount = data?.activeCount ?? 0;
  const criticalCount = data?.criticalCount ?? 0;

  return {
    alerts,
    activeCount,
    criticalCount,
    total: data?.total ?? 0,
    isLoading,
    isError,
    error: error as Error | null,
    refetch,
    acknowledge: handleAcknowledge,
    dismiss: handleDismiss,
    isAcknowledging: acknowledgeMutation.isPending,
    isDismissing: dismissMutation.isPending,
    hasCriticalAlerts: criticalCount > 0,
    hasActiveAlerts: activeCount > 0,
  };
}

// ============================================
// useLoadAnalysis Hook
// ============================================

export interface UseLoadAnalysisReturn {
  data: LoadAnalysisData | null;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => void;
  hasSpikeAlert: boolean;
  hasHighMonotony: boolean;
  hasHighStrain: boolean;
  overallRisk: AlertSeverity;
}

/**
 * Hook for fetching comprehensive training load analysis.
 *
 * Includes spike detection, monotony/strain calculations,
 * and risk assessment.
 */
export function useLoadAnalysis(enabled = true): UseLoadAnalysisReturn {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: safetyKeys.loadAnalysis(),
    queryFn: getLoadAnalysis,
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const hasSpikeAlert = data?.spikeResult?.spikeDetected ?? false;
  const hasHighMonotony =
    data?.monotonyStrain?.monotonyRisk !== 'info' &&
    data?.monotonyStrain?.monotonyRisk !== undefined;
  const hasHighStrain =
    data?.monotonyStrain?.strainRisk !== 'info' &&
    data?.monotonyStrain?.strainRisk !== undefined;

  return {
    data: data ?? null,
    isLoading,
    isError,
    error: error as Error | null,
    refetch,
    hasSpikeAlert,
    hasHighMonotony,
    hasHighStrain,
    overallRisk: data?.overallRisk ?? 'info',
  };
}

// ============================================
// useActiveAlerts Hook (Convenience)
// ============================================

/**
 * Convenience hook for fetching only active alerts.
 * Auto-refreshes every 5 minutes.
 */
export function useActiveAlerts() {
  return useSafetyAlerts({
    status: 'active',
    refetchInterval: 5 * 60 * 1000, // 5 minutes
  });
}

// ============================================
// useCriticalAlerts Hook (Convenience)
// ============================================

/**
 * Convenience hook for fetching only critical alerts.
 * Auto-refreshes every 2 minutes for urgent monitoring.
 */
export function useCriticalAlerts() {
  return useSafetyAlerts({
    status: 'active',
    severity: 'critical',
    refetchInterval: 2 * 60 * 1000, // 2 minutes
  });
}

export default useSafetyAlerts;
