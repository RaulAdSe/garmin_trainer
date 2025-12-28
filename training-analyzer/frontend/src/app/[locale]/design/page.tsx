'use client';

import { useSearchParams } from 'next/navigation';
import { useRouter } from '@/i18n/navigation';
import { useCallback, Suspense } from 'react';
import { useQuery } from '@tanstack/react-query';
import { WorkoutDesigner } from '@/components/design/WorkoutDesigner';
import { getDesignedWorkout } from '@/lib/api-client';
import type { DesignedWorkout } from '@/lib/types';

function DesignPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const workoutId = searchParams.get('id');

  // Fetch existing workout if editing
  const {
    data: existingWorkout,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['designed-workout', workoutId],
    queryFn: () => getDesignedWorkout(workoutId!),
    enabled: !!workoutId,
  });

  const handleSave = useCallback(
    (workout: DesignedWorkout) => {
      // If this is a new workout, redirect to the edit page with the new ID
      if (workout.id && !workoutId) {
        router.replace(`/design?id=${workout.id}`);
      }
    },
    [router, workoutId]
  );

  const handleCancel = useCallback(() => {
    router.back();
  }, [router]);

  // Loading state
  if (workoutId && isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-gray-200 dark:bg-gray-800 rounded w-1/3" />
            <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-1/2" />
            <div className="h-64 bg-gray-200 dark:bg-gray-800 rounded" />
            <div className="h-48 bg-gray-200 dark:bg-gray-800 rounded" />
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 text-center">
            <svg
              className="w-12 h-12 mx-auto text-red-400 mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <h2 className="text-lg font-semibold text-red-800 dark:text-red-200 mb-2">
              Failed to load workout
            </h2>
            <p className="text-red-600 dark:text-red-400 mb-4">
              {error instanceof Error ? error.message : 'An error occurred'}
            </p>
            <button
              onClick={() => router.push('/design')}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Create New Workout
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <WorkoutDesigner
          initialWorkout={existingWorkout}
          onSave={handleSave}
          onCancel={handleCancel}
        />
      </div>
    </div>
  );
}

export default function DesignPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="animate-pulse space-y-6">
              <div className="h-8 bg-gray-200 dark:bg-gray-800 rounded w-1/3" />
              <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-1/2" />
              <div className="h-64 bg-gray-200 dark:bg-gray-800 rounded" />
            </div>
          </div>
        </div>
      }
    >
      <DesignPageContent />
    </Suspense>
  );
}
