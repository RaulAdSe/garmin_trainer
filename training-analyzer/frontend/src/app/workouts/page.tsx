'use client';

import { useState } from 'react';
import { useWorkouts } from '@/hooks/useWorkouts';
import { WorkoutList } from '@/components/workouts/WorkoutList';
import type { WorkoutListFilters } from '@/lib/types';

export default function WorkoutsPage() {
  const [filters, setFilters] = useState<WorkoutListFilters>({});

  const {
    workouts,
    total,
    page,
    totalPages,
    isLoading,
    isError,
    error,
    analyses,
    loadingAnalysisId,
    analyzeWorkout,
    setPage,
    setFilters: updateFilters,
  } = useWorkouts({
    pageSize: 10,
    filters,
  });

  const handleFiltersChange = (newFilters: WorkoutListFilters) => {
    setFilters(newFilters);
    updateFilters(newFilters);
  };

  const handleLoadMore = () => {
    if (page < totalPages) {
      setPage(page + 1);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Workouts</h1>
          <p className="mt-1 text-sm text-gray-400">
            View and analyze your training history
          </p>
        </div>

        {/* Stats summary */}
        {total > 0 && (
          <div className="hidden sm:flex items-center gap-6">
            <StatCard label="Total Workouts" value={total.toString()} />
            <StatCard
              label="This Week"
              value={getThisWeekCount(workouts).toString()}
            />
          </div>
        )}
      </div>

      {/* Main content */}
      <div>
        {isError ? (
          <ErrorMessage message={error?.message || 'Failed to load workouts'} />
        ) : (
          <WorkoutList
            workouts={workouts}
            analyses={analyses}
            isLoading={isLoading}
            hasMore={page < totalPages}
            onLoadMore={handleLoadMore}
            onAnalyze={analyzeWorkout}
            analyzingWorkoutId={loadingAnalysisId}
            filters={filters}
            onFiltersChange={handleFiltersChange}
          />
        )}

        {/* Pagination info */}
        {total > 0 && (
          <div className="mt-6 text-center text-sm text-gray-500">
            Showing {workouts.length} of {total} workouts
            {totalPages > 1 && ` (Page ${page} of ${totalPages})`}
          </div>
        )}
      </div>
    </div>
  );
}

// Helper components
function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center">
      <dt className="text-xs text-gray-500 uppercase tracking-wide">{label}</dt>
      <dd className="text-xl font-semibold text-teal-400">{value}</dd>
    </div>
  );
}

function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="bg-red-900/20 border border-red-800 rounded-lg p-6 text-center">
      <div className="inline-flex items-center justify-center w-12 h-12 bg-red-900/50 rounded-full mb-4">
        <svg
          className="w-6 h-6 text-red-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-red-300 mb-1">
        Error Loading Workouts
      </h3>
      <p className="text-sm text-red-400">{message}</p>
      <button
        onClick={() => window.location.reload()}
        className="mt-4 px-4 py-2 bg-red-900/50 text-red-300 rounded-md text-sm hover:bg-red-900 transition-colors"
      >
        Try Again
      </button>
    </div>
  );
}

// Helper function to count workouts this week
function getThisWeekCount(workouts: { date: string }[]): number {
  const now = new Date();
  const startOfWeek = new Date(now);
  startOfWeek.setDate(now.getDate() - now.getDay());
  startOfWeek.setHours(0, 0, 0, 0);

  return workouts.filter((w) => new Date(w.date) >= startOfWeek).length;
}
