'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import { usePRHistory, useRecentPRs } from '@/hooks/usePRDetection';
import { PRBadge } from './PRBadge';
import type { PRType } from './PRCelebrationModal';

/**
 * Personal Record data structure from API
 */
export interface PersonalRecord {
  id: string;
  userId: string;
  prType: PRType;
  activityType: string;
  value: number;
  unit: string;
  workoutId: string;
  achievedAt: string;
  previousValue: number | null;
  improvement: number | null;
  improvementPercent: number | null;
  workoutName: string | null;
  workoutDate: string | null;
}

/**
 * Filter options for PR history
 */
type PRFilter = 'all' | PRType;

interface PRHistoryProps {
  className?: string;
}

/**
 * Format a PR value for display
 */
function formatPRValue(value: number, unit: string, prType: PRType): string {
  if (prType === 'pace') {
    const minutes = Math.floor(value / 60);
    const seconds = Math.round(value % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')} /km`;
  }
  if (prType === 'distance') {
    const km = value / 1000;
    return km >= 1 ? `${km.toFixed(2)} km` : `${value.toFixed(0)} m`;
  }
  if (prType === 'duration') {
    const hours = Math.floor(value / 3600);
    const minutes = Math.floor((value % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes} min`;
  }
  if (prType === 'elevation') {
    return `${value.toFixed(0)} m`;
  }
  if (prType === 'power') {
    return `${value.toFixed(0)} W`;
  }
  return `${value} ${unit}`;
}

/**
 * Format a date string for display
 */
function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * PRHistoryItem Component
 */
function PRHistoryItem({ pr }: { pr: PersonalRecord }) {
  const t = useTranslations('personalRecords');

  return (
    <div className="flex items-center gap-4 p-4 bg-gray-800/50 rounded-xl border border-gray-700/50 hover:border-gray-600/50 transition-colors">
      {/* PR Badge */}
      <div className="flex-shrink-0">
        <PRBadge prType={pr.prType} size="lg" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium text-amber-400">
            {t(`prTypes.${pr.prType}`)}
          </span>
          <span className="text-xs text-gray-500">
            {t(`activityTypes.${pr.activityType}`)}
          </span>
        </div>

        {/* Value */}
        <div className="text-lg font-semibold text-white">
          {formatPRValue(pr.value, pr.unit, pr.prType)}
        </div>

        {/* Improvement */}
        {pr.improvement !== null && pr.previousValue !== null && (
          <div className="flex items-center gap-2 mt-1 text-sm">
            <span className="text-gray-500 line-through">
              {formatPRValue(pr.previousValue, pr.unit, pr.prType)}
            </span>
            <span className="text-green-400">
              {pr.prType === 'pace' ? (
                <>-{Math.abs(pr.improvement).toFixed(0)}s</>
              ) : pr.improvementPercent !== null ? (
                <>+{pr.improvementPercent.toFixed(1)}%</>
              ) : null}
            </span>
          </div>
        )}
      </div>

      {/* Date & Workout Info */}
      <div className="flex-shrink-0 text-right">
        <div className="text-sm text-gray-400">
          {formatDate(pr.achievedAt)}
        </div>
        {pr.workoutName && (
          <div className="text-xs text-gray-500 truncate max-w-[120px]">
            {pr.workoutName}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * PRHistory Component
 *
 * Displays a timeline of all personal records with filtering by type.
 */
export function PRHistory({ className }: PRHistoryProps) {
  const t = useTranslations('personalRecords');
  const [filter, setFilter] = useState<PRFilter>('all');
  const [viewMode, setViewMode] = useState<'timeline' | 'recent'>('timeline');

  const { data: historyData, isLoading: isLoadingHistory } = usePRHistory(
    filter === 'all' ? undefined : filter
  );
  const { data: recentData, isLoading: isLoadingRecent } = useRecentPRs(30);

  const isLoading = viewMode === 'timeline' ? isLoadingHistory : isLoadingRecent;
  const prs = viewMode === 'timeline'
    ? historyData?.personalRecords || []
    : recentData?.personalRecords || [];

  const filterOptions: { value: PRFilter; label: string }[] = [
    { value: 'all', label: t('filters.all') },
    { value: 'pace', label: t('prTypes.pace') },
    { value: 'distance', label: t('prTypes.distance') },
    { value: 'duration', label: t('prTypes.duration') },
    { value: 'elevation', label: t('prTypes.elevation') },
    { value: 'power', label: t('prTypes.power') },
  ];

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">
          {t('history.title')}
        </h3>

        {/* View mode toggle */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode('timeline')}
            className={cn(
              'px-3 py-1.5 text-sm rounded-lg transition-colors',
              viewMode === 'timeline'
                ? 'bg-amber-500/20 text-amber-400'
                : 'text-gray-400 hover:text-gray-300'
            )}
          >
            {t('history.viewModes.timeline')}
          </button>
          <button
            onClick={() => setViewMode('recent')}
            className={cn(
              'px-3 py-1.5 text-sm rounded-lg transition-colors',
              viewMode === 'recent'
                ? 'bg-amber-500/20 text-amber-400'
                : 'text-gray-400 hover:text-gray-300'
            )}
          >
            {t('history.viewModes.recent')}
          </button>
        </div>
      </div>

      {/* Filter tabs */}
      {viewMode === 'timeline' && (
        <div className="flex flex-wrap gap-2">
          {filterOptions.map((option) => (
            <button
              key={option.value}
              onClick={() => setFilter(option.value)}
              className={cn(
                'px-3 py-1.5 text-sm rounded-full border transition-colors',
                filter === option.value
                  ? 'bg-amber-500/20 border-amber-500/50 text-amber-400'
                  : 'border-gray-700 text-gray-400 hover:border-gray-600 hover:text-gray-300'
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Empty state */}
      {!isLoading && prs.length === 0 && (
        <div className="text-center py-12">
          <div className="text-4xl mb-4">
            <svg className="w-12 h-12 mx-auto text-gray-600" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            </svg>
          </div>
          <p className="text-gray-500">
            {t('history.empty')}
          </p>
        </div>
      )}

      {/* PR List */}
      {!isLoading && prs.length > 0 && (
        <div className="space-y-3">
          {prs.map((pr) => (
            <PRHistoryItem key={pr.id} pr={pr} />
          ))}
        </div>
      )}

      {/* Summary */}
      {historyData?.summary && viewMode === 'timeline' && (
        <div className="mt-6 p-4 bg-gray-800/30 rounded-xl border border-gray-700/50">
          <h4 className="text-sm font-medium text-gray-400 mb-3">
            {t('history.summary.title')}
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-2xl font-bold text-white">
                {historyData.summary.totalPrs}
              </div>
              <div className="text-xs text-gray-500">
                {t('history.summary.totalPRs')}
              </div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-400">
                {historyData.summary.recentPrs}
              </div>
              <div className="text-xs text-gray-500">
                {t('history.summary.last30Days')}
              </div>
            </div>
            {historyData.summary.latestPr && (
              <div className="col-span-2">
                <div className="text-sm text-amber-400">
                  {t('history.summary.latestPR')}
                </div>
                <div className="text-sm text-gray-300">
                  {t(`prTypes.${historyData.summary.latestPr.prType}`)} -{' '}
                  {formatPRValue(
                    historyData.summary.latestPr.value,
                    historyData.summary.latestPr.unit,
                    historyData.summary.latestPr.prType
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default PRHistory;
