'use client';

import { useCallback, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useWorkouts } from '@/hooks/useWorkouts';
import { WorkoutList } from '@/components/workouts/WorkoutList';
import { GarminSync } from '@/components/garmin/GarminSync';
import { Button } from '@/components/ui/Button';
import type { WorkoutListFilters } from '@/lib/types';
import type { GarminSyncResponse } from '@/lib/api-client';

export default function WorkoutsPage() {
  const t = useTranslations('workouts');
  const [showGarminSync, setShowGarminSync] = useState(false);

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
    filters,
    setFilters: updateFilters,
    refetch,
  } = useWorkouts({
    pageSize: 10,
  });

  const handleSyncComplete = useCallback((result: GarminSyncResponse) => {
    // Refetch workouts after successful sync
    if (result.success && result.synced_count > 0) {
      refetch();
    }
  }, [refetch]);

  const handleCloseSyncModal = useCallback(() => {
    setShowGarminSync(false);
  }, []);

  const handleFiltersChange = (newFilters: WorkoutListFilters) => {
    updateFilters(newFilters);
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    // Scroll to top when changing pages
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">{t('title')}</h1>
          <p className="mt-1 text-sm text-gray-400">
            {t('subtitle')}
          </p>
        </div>

        <div className="flex items-center gap-4">
          {/* Stats summary */}
          {total > 0 && (
            <div className="hidden sm:flex items-center gap-6">
              <StatCard label={t('totalWorkouts')} value={total.toString()} />
              <StatCard
                label={t('thisWeek')}
                value={getThisWeekCount(workouts).toString()}
              />
            </div>
          )}

          {/* Garmin Sync Button */}
          <Button
            variant="primary"
            onClick={() => setShowGarminSync(true)}
            leftIcon={<SyncIcon className="w-4 h-4" />}
          >
            {t('syncGarmin')}
          </Button>
        </div>
      </div>

      {/* Garmin Sync Modal */}
      {showGarminSync && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="w-full max-w-md mx-4">
            <GarminSync
              onSyncComplete={handleSyncComplete}
              onClose={handleCloseSyncModal}
            />
          </div>
        </div>
      )}

      {/* Main content */}
      <div>
        {isError ? (
          <ErrorMessage
            title={t('errorLoading')}
            message={error?.message || 'Failed to load workouts'}
            retryLabel={t('tryAgain')}
          />
        ) : (
          <WorkoutList
            workouts={workouts}
            analyses={analyses}
            isLoading={isLoading}
            currentPage={page}
            totalPages={totalPages}
            totalWorkouts={total}
            onPageChange={handlePageChange}
            onAnalyze={analyzeWorkout}
            analyzingWorkoutId={loadingAnalysisId}
            filters={filters}
            onFiltersChange={handleFiltersChange}
          />
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

function ErrorMessage({ title, message, retryLabel }: { title: string; message: string; retryLabel: string }) {
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
        {title}
      </h3>
      <p className="text-sm text-red-400">{message}</p>
      <button
        onClick={() => window.location.reload()}
        className="mt-4 px-4 py-2 bg-red-900/50 text-red-300 rounded-md text-sm hover:bg-red-900 transition-colors"
      >
        {retryLabel}
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

// Sync icon component
function SyncIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
      />
    </svg>
  );
}
