'use client';

import { useState, useCallback, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  downloadWorkoutFIT,
  exportWorkoutToGarmin,
  checkGarminConnection,
} from '@/lib/api-client';
import type { GarminExportResponse } from '@/lib/types';

interface UseFITExportReturn {
  // Download FIT file
  downloadFIT: (workoutId: string, workoutName: string) => Promise<void>;
  isDownloading: boolean;
  downloadError: Error | null;

  // Export to Garmin Connect
  exportToGarmin: (workoutId: string) => Promise<GarminExportResponse>;
  isExporting: boolean;
  exportError: Error | null;

  // Garmin connection status
  garminConnected: boolean;
  checkingConnection: boolean;
  refreshConnectionStatus: () => void;
}

export function useFITExport(): UseFITExportReturn {
  const [downloadError, setDownloadError] = useState<Error | null>(null);
  const [exportError, setExportError] = useState<Error | null>(null);

  // Check Garmin connection status
  const {
    data: connectionStatus,
    isLoading: checkingConnection,
    refetch: refreshConnectionStatus,
  } = useQuery({
    queryKey: ['garmin-connection'],
    queryFn: checkGarminConnection,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false,
  });

  // Download FIT mutation
  const downloadMutation = useMutation({
    mutationFn: async ({
      workoutId,
      workoutName,
    }: {
      workoutId: string;
      workoutName: string;
    }) => {
      const blob = await downloadWorkoutFIT(workoutId);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;

      // Generate filename
      const safeName = workoutName
        .replace(/[^a-z0-9]/gi, '_')
        .toLowerCase()
        .substring(0, 50);
      const timestamp = new Date().toISOString().slice(0, 10);
      link.download = `${safeName}_${timestamp}.fit`;

      // Trigger download
      document.body.appendChild(link);
      link.click();

      // Cleanup
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },
    onError: (error) => {
      setDownloadError(
        error instanceof Error ? error : new Error('Download failed')
      );
    },
    onSuccess: () => {
      setDownloadError(null);
    },
  });

  // Export to Garmin mutation
  const exportMutation = useMutation({
    mutationFn: exportWorkoutToGarmin,
    onError: (error) => {
      setExportError(
        error instanceof Error ? error : new Error('Export failed')
      );
    },
    onSuccess: () => {
      setExportError(null);
    },
  });

  // Download handler
  const downloadFIT = useCallback(
    async (workoutId: string, workoutName: string) => {
      await downloadMutation.mutateAsync({ workoutId, workoutName });
    },
    [downloadMutation]
  );

  // Export handler
  const exportToGarmin = useCallback(
    async (workoutId: string): Promise<GarminExportResponse> => {
      return await exportMutation.mutateAsync(workoutId);
    },
    [exportMutation]
  );

  // Clear errors after timeout
  useEffect(() => {
    if (downloadError) {
      const timer = setTimeout(() => setDownloadError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [downloadError]);

  useEffect(() => {
    if (exportError) {
      const timer = setTimeout(() => setExportError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [exportError]);

  return {
    // Download
    downloadFIT,
    isDownloading: downloadMutation.isPending,
    downloadError,

    // Export
    exportToGarmin,
    isExporting: exportMutation.isPending,
    exportError,

    // Connection status
    garminConnected: connectionStatus?.connected ?? false,
    checkingConnection,
    refreshConnectionStatus: () => refreshConnectionStatus(),
  };
}

// Hook for batch FIT operations
export function useBatchFITExport() {
  const [progress, setProgress] = useState<{
    current: number;
    total: number;
    currentWorkout: string;
  } | null>(null);

  const { downloadFIT } = useFITExport();

  const downloadMultiple = useCallback(
    async (workouts: { id: string; name: string }[]) => {
      setProgress({ current: 0, total: workouts.length, currentWorkout: '' });

      for (let i = 0; i < workouts.length; i++) {
        const workout = workouts[i];
        setProgress({
          current: i + 1,
          total: workouts.length,
          currentWorkout: workout.name,
        });

        try {
          await downloadFIT(workout.id, workout.name);
          // Small delay between downloads
          await new Promise((resolve) => setTimeout(resolve, 500));
        } catch (error) {
          console.error(`Failed to download ${workout.name}:`, error);
          // Continue with other downloads
        }
      }

      setProgress(null);
    },
    [downloadFIT]
  );

  return {
    downloadMultiple,
    progress,
    isDownloading: progress !== null,
  };
}

export default useFITExport;
