'use client';

import { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import type { ComparisonTarget, NormalizationMode } from '@/types/comparison';

interface ComparisonSelectorProps {
  /**
   * List of comparable workouts from API.
   */
  comparableWorkouts: ComparisonTarget[];

  /**
   * Quick selection workouts (Best 10K, Last Similar, etc).
   */
  quickSelections: ComparisonTarget[];

  /**
   * Currently selected comparison workout ID.
   */
  selectedId: string | null;

  /**
   * Callback when a workout is selected.
   */
  onSelect: (workoutId: string) => void;

  /**
   * Callback to clear the selection.
   */
  onClear: () => void;

  /**
   * Current normalization mode.
   */
  normalizationMode: NormalizationMode;

  /**
   * Callback when normalization mode changes.
   */
  onNormalizationModeChange: (mode: NormalizationMode) => void;

  /**
   * Whether the selector is loading data.
   */
  isLoading?: boolean;

  /**
   * Optional class name.
   */
  className?: string;
}

/**
 * Dropdown selector for choosing a comparison workout.
 * Includes quick selection buttons and filters.
 */
export function ComparisonSelector({
  comparableWorkouts,
  quickSelections,
  selectedId,
  onSelect,
  onClear,
  normalizationMode,
  onNormalizationModeChange,
  isLoading = false,
  className = '',
}: ComparisonSelectorProps) {
  const t = useTranslations('comparison');
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Find the currently selected workout
  const selectedWorkout = useMemo(() => {
    if (!selectedId) return null;
    return (
      comparableWorkouts.find((w) => w.activity_id === selectedId) ||
      quickSelections.find((w) => w.activity_id === selectedId)
    );
  }, [selectedId, comparableWorkouts, quickSelections]);

  // Filter workouts by search query
  const filteredWorkouts = useMemo(() => {
    if (!searchQuery) return comparableWorkouts;
    const query = searchQuery.toLowerCase();
    return comparableWorkouts.filter(
      (w) =>
        w.name.toLowerCase().includes(query) ||
        w.activity_type.toLowerCase().includes(query) ||
        w.date.includes(query)
    );
  }, [comparableWorkouts, searchQuery]);

  // Handle workout selection
  const handleSelect = useCallback(
    (workoutId: string) => {
      onSelect(workoutId);
      setIsOpen(false);
      setSearchQuery('');
    },
    [onSelect]
  );

  // Format date for display
  const formatDate = (dateStr: string): string => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  // Format duration for display
  const formatDuration = (minutes: number): string => {
    const hours = Math.floor(minutes / 60);
    const mins = Math.round(minutes % 60);
    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  };

  // Format pace for display
  const formatPace = (secPerKm: number | undefined): string => {
    if (!secPerKm) return '--';
    const mins = Math.floor(secPerKm / 60);
    const secs = Math.round(secPerKm % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}/km`;
  };

  // Get quick selection label
  const getQuickSelectionLabel = (type: string | undefined): string => {
    if (!type) return '';
    const labels: Record<string, string> = {
      last_similar: t('quickSelect.lastSimilar'),
      best_pace: t('quickSelect.bestPace'),
      best_5k: t('quickSelect.best5k'),
      best_10k: t('quickSelect.best10k'),
      best_half_marathon: t('quickSelect.bestHalf'),
      best_marathon: t('quickSelect.bestMarathon'),
    };
    return labels[type] ?? type;
  };

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      {/* Main toggle button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading}
        className={`
          flex items-center justify-between gap-2 px-3 py-2 w-full
          bg-gray-800 border border-gray-700 rounded-lg
          text-sm text-left
          hover:bg-gray-750 hover:border-gray-600
          focus:outline-none focus:ring-2 focus:ring-teal-500/50
          disabled:opacity-50 disabled:cursor-not-allowed
          transition-colors duration-200
        `}
      >
        <div className="flex items-center gap-2 min-w-0">
          {/* Comparison icon */}
          <svg
            className="w-4 h-4 text-amber-400 flex-shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>

          {/* Selected workout display */}
          {selectedWorkout ? (
            <span className="truncate text-gray-200">
              {selectedWorkout.quick_selection_type
                ? getQuickSelectionLabel(selectedWorkout.quick_selection_type)
                : selectedWorkout.name}
            </span>
          ) : (
            <span className="text-gray-400">{t('selector.placeholder')}</span>
          )}
        </div>

        {/* Clear button or chevron */}
        {selectedWorkout ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onClear();
            }}
            className="p-0.5 hover:bg-gray-700 rounded transition-colors"
            aria-label={t('selector.clear')}
          >
            <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        ) : (
          <svg
            className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        )}
      </button>

      {/* Dropdown panel */}
      {isOpen && (
        <div className="absolute z-50 mt-1 w-full min-w-[280px] max-h-[400px] overflow-auto bg-gray-800 border border-gray-700 rounded-lg shadow-xl animate-in fade-in slide-in-from-top-2 duration-200">
          {/* Quick selections */}
          {quickSelections.length > 0 && (
            <div className="p-2 border-b border-gray-700">
              <p className="text-xs font-medium text-gray-400 mb-2 px-1">
                {t('selector.quickSelections')}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {quickSelections.map((workout) => (
                  <button
                    key={workout.activity_id}
                    type="button"
                    onClick={() => handleSelect(workout.activity_id)}
                    className={`
                      inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-xs font-medium
                      transition-colors duration-150
                      ${
                        selectedId === workout.activity_id
                          ? 'bg-amber-500/20 text-amber-400 ring-1 ring-amber-500/50'
                          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                      }
                    `}
                  >
                    {workout.is_pr && (
                      <svg className="w-3 h-3 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                    )}
                    {getQuickSelectionLabel(workout.quick_selection_type)}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Search input */}
          <div className="p-2 border-b border-gray-700">
            <div className="relative">
              <svg
                className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t('selector.searchPlaceholder')}
                className="w-full pl-8 pr-3 py-1.5 bg-gray-900 border border-gray-700 rounded text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-teal-500/50 focus:border-teal-500/50"
              />
            </div>
          </div>

          {/* Normalization mode toggle */}
          <div className="p-2 border-b border-gray-700">
            <p className="text-xs font-medium text-gray-400 mb-2 px-1">
              {t('selector.normalizeBy')}
            </p>
            <div className="flex gap-1">
              {(['percentage', 'time', 'distance'] as NormalizationMode[]).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => onNormalizationModeChange(mode)}
                  className={`
                    flex-1 px-2 py-1 rounded text-xs font-medium transition-colors
                    ${
                      normalizationMode === mode
                        ? 'bg-teal-500/20 text-teal-400'
                        : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                    }
                  `}
                >
                  {t(`normalizeMode.${mode}`)}
                </button>
              ))}
            </div>
          </div>

          {/* Workout list */}
          <div className="max-h-[200px] overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-6 w-6 border-2 border-teal-400 border-t-transparent" />
              </div>
            ) : filteredWorkouts.length === 0 ? (
              <div className="py-8 text-center text-gray-500 text-sm">
                {searchQuery ? t('selector.noResults') : t('selector.noWorkouts')}
              </div>
            ) : (
              <ul className="py-1">
                {filteredWorkouts.map((workout) => (
                  <li key={workout.activity_id}>
                    <button
                      type="button"
                      onClick={() => handleSelect(workout.activity_id)}
                      className={`
                        w-full px-3 py-2 text-left hover:bg-gray-700/50 transition-colors
                        ${selectedId === workout.activity_id ? 'bg-gray-700/50' : ''}
                      `}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-200 truncate">{workout.name}</span>
                        {workout.is_pr && (
                          <span className="text-xs text-amber-400 ml-2">PR</span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 mt-0.5 text-xs text-gray-500">
                        <span>{formatDate(workout.date)}</span>
                        <span>{formatDuration(workout.duration_min)}</span>
                        {workout.distance_km && <span>{workout.distance_km.toFixed(1)} km</span>}
                        {workout.avg_pace_sec_km && <span>{formatPace(workout.avg_pace_sec_km)}</span>}
                      </div>
                      {/* Similarity bar */}
                      <div className="mt-1.5 h-1 bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-teal-500/50 rounded-full"
                          style={{ width: `${Math.round(workout.similarity_score * 100)}%` }}
                        />
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default ComparisonSelector;
