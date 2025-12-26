'use client';

import { useState } from 'react';
import type { Workout, WorkoutAnalysis, WorkoutType, WorkoutListFilters } from '@/lib/types';
import { WorkoutCard } from './WorkoutCard';
import { cn, getWorkoutTypeLabel } from '@/lib/utils';

interface WorkoutListProps {
  workouts: Workout[];
  analyses?: Map<string, WorkoutAnalysis>;
  isLoading?: boolean;
  hasMore?: boolean;
  onLoadMore?: () => void;
  onAnalyze?: (workoutId: string) => void;
  analyzingWorkoutId?: string | null;
  filters?: WorkoutListFilters;
  onFiltersChange?: (filters: WorkoutListFilters) => void;
  className?: string;
}

export function WorkoutList({
  workouts,
  analyses = new Map(),
  isLoading = false,
  hasMore = false,
  onLoadMore,
  onAnalyze,
  analyzingWorkoutId,
  filters,
  onFiltersChange,
  className,
}: WorkoutListProps) {
  const [showFilters, setShowFilters] = useState(false);

  const hasActiveFilters = filters && (
    filters.startDate ||
    filters.endDate ||
    filters.type ||
    filters.minDistance ||
    filters.maxDistance ||
    filters.search
  );

  return (
    <div className={cn('space-y-4', className)}>
      {/* Filter Bar */}
      {onFiltersChange && (
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* Search input */}
              <div className="relative">
                <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  placeholder="Search workouts..."
                  value={filters?.search || ''}
                  onChange={(e) =>
                    onFiltersChange({ ...filters, search: e.target.value })
                  }
                  className="pl-9 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-md text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent w-64"
                />
              </div>

              {/* Type filter */}
              <select
                value={filters?.type || ''}
                onChange={(e) =>
                  onFiltersChange({
                    ...filters,
                    type: e.target.value as WorkoutType | undefined || undefined,
                  })
                }
                className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-md text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              >
                <option value="">All Types</option>
                <option value="running">{getWorkoutTypeLabel('running')}</option>
                <option value="cycling">{getWorkoutTypeLabel('cycling')}</option>
                <option value="swimming">{getWorkoutTypeLabel('swimming')}</option>
                <option value="strength">{getWorkoutTypeLabel('strength')}</option>
                <option value="hiit">{getWorkoutTypeLabel('hiit')}</option>
                <option value="yoga">{getWorkoutTypeLabel('yoga')}</option>
                <option value="walking">{getWorkoutTypeLabel('walking')}</option>
              </select>

              {/* Toggle advanced filters */}
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={cn(
                  'flex items-center gap-1 px-3 py-2 text-sm rounded-md transition-colors',
                  showFilters || hasActiveFilters
                    ? 'bg-teal-900/50 text-teal-400'
                    : 'text-gray-400 hover:bg-gray-800'
                )}
              >
                <FilterIcon />
                <span>Filters</span>
                {hasActiveFilters && (
                  <span className="ml-1 w-2 h-2 bg-teal-400 rounded-full" />
                )}
              </button>
            </div>

            {/* Results count */}
            <span className="text-sm text-gray-500">
              {workouts.length} workout{workouts.length !== 1 ? 's' : ''}
            </span>
          </div>

          {/* Advanced filters */}
          {showFilters && (
            <div className="mt-4 pt-4 border-t border-gray-800">
              <div className="grid grid-cols-4 gap-4">
                {/* Date range */}
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
                    From Date
                  </label>
                  <input
                    type="date"
                    value={filters?.startDate || ''}
                    onChange={(e) =>
                      onFiltersChange({ ...filters, startDate: e.target.value || undefined })
                    }
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-md text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
                    To Date
                  </label>
                  <input
                    type="date"
                    value={filters?.endDate || ''}
                    onChange={(e) =>
                      onFiltersChange({ ...filters, endDate: e.target.value || undefined })
                    }
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-md text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>

                {/* Distance range */}
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
                    Min Distance (km)
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="0.1"
                    value={filters?.minDistance ? filters.minDistance / 1000 : ''}
                    onChange={(e) =>
                      onFiltersChange({
                        ...filters,
                        minDistance: e.target.value ? parseFloat(e.target.value) * 1000 : undefined,
                      })
                    }
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-md text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
                    Max Distance (km)
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="0.1"
                    value={filters?.maxDistance ? filters.maxDistance / 1000 : ''}
                    onChange={(e) =>
                      onFiltersChange({
                        ...filters,
                        maxDistance: e.target.value ? parseFloat(e.target.value) * 1000 : undefined,
                      })
                    }
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-md text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>
              </div>

              {/* Clear filters */}
              {hasActiveFilters && (
                <button
                  onClick={() => onFiltersChange({})}
                  className="mt-3 text-sm text-teal-400 hover:text-teal-300"
                >
                  Clear all filters
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Workout cards */}
      {isLoading && workouts.length === 0 ? (
        <WorkoutListSkeleton count={3} />
      ) : workouts.length === 0 ? (
        <EmptyState hasFilters={!!hasActiveFilters} />
      ) : (
        <div className="space-y-4">
          {workouts.map((workout) => (
            <WorkoutCard
              key={workout.id}
              workout={workout}
              analysis={analyses.get(workout.id)}
              onAnalyze={() => onAnalyze?.(workout.id)}
              isAnalyzing={analyzingWorkoutId === workout.id}
            />
          ))}
        </div>
      )}

      {/* Load more button */}
      {hasMore && (
        <div className="flex justify-center pt-4">
          <button
            onClick={onLoadMore}
            disabled={isLoading}
            className={cn(
              'px-6 py-2 rounded-md text-sm font-medium transition-colors',
              isLoading
                ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                : 'bg-teal-900/50 text-teal-400 hover:bg-teal-900'
            )}
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <LoadingSpinner />
                Loading...
              </span>
            ) : (
              'Load More Workouts'
            )}
          </button>
        </div>
      )}
    </div>
  );
}

// Empty state component
function EmptyState({ hasFilters }: { hasFilters: boolean }) {
  return (
    <div className="bg-gray-900 rounded-lg border border-gray-800 p-8 text-center">
      <div className="inline-flex items-center justify-center w-12 h-12 bg-gray-800 rounded-full mb-4">
        <EmptyIcon className="w-6 h-6 text-gray-500" />
      </div>
      <h3 className="text-lg font-medium text-gray-100 mb-1">
        {hasFilters ? 'No matching workouts' : 'No workouts yet'}
      </h3>
      <p className="text-sm text-gray-400">
        {hasFilters
          ? 'Try adjusting your filters to find workouts.'
          : 'Your workout history will appear here once you sync data from Garmin.'}
      </p>
    </div>
  );
}

// Skeleton loader
function WorkoutListSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="bg-gray-900 rounded-lg border border-gray-800 p-4 animate-pulse"
        >
          <div className="flex items-start justify-between mb-3">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-5 h-5 bg-gray-800 rounded" />
                <div className="w-32 h-5 bg-gray-800 rounded" />
              </div>
              <div className="w-48 h-4 bg-gray-800 rounded" />
            </div>
            <div className="w-20 h-4 bg-gray-800 rounded" />
          </div>

          <div className="grid grid-cols-4 gap-4 mb-3">
            {[1, 2, 3, 4].map((j) => (
              <div key={j}>
                <div className="w-12 h-3 bg-gray-800 rounded mb-1" />
                <div className="w-16 h-4 bg-gray-700 rounded" />
              </div>
            ))}
          </div>

          <div className="h-2 bg-gray-800 rounded-full mb-3" />

          <div className="flex items-center justify-between pt-2 border-t border-gray-800">
            <div className="w-32 h-8 bg-gray-800 rounded" />
            <div className="w-16 h-4 bg-gray-800 rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}

// Icon components
function SearchIcon({ className }: { className?: string }) {
  return (
    <svg className={cn('w-5 h-5', className)} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
      />
    </svg>
  );
}

function FilterIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
      />
    </svg>
  );
}

function EmptyIcon({ className }: { className?: string }) {
  return (
    <svg className={cn('w-6 h-6', className)} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
      />
    </svg>
  );
}

function LoadingSpinner() {
  return (
    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

export default WorkoutList;
