'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import type { Workout, WorkoutAnalysis } from '@/lib/types';
import {
  cn,
  formatDuration,
  formatPace,
  formatDistance,
  formatDate,
  getRelativeTime,
  getWorkoutTypeLabel,
  getHRZoneColor,
  getHRZoneLabel,
} from '@/lib/utils';

interface WorkoutCardProps {
  workout: Workout;
  analysis?: WorkoutAnalysis | null;
  onAnalyze?: () => void;
  isAnalyzing?: boolean;
  className?: string;
}

export function WorkoutCard({
  workout,
  analysis,
  onAnalyze,
  isAnalyzing = false,
  className,
}: WorkoutCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const hasAnalysis = !!analysis;

  const toggleExpanded = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  return (
    <article
      className={cn(
        'bg-gray-900 rounded-xl border border-gray-800 overflow-hidden transition-all duration-200',
        'hover:border-gray-700 active:bg-gray-800/50',
        className
      )}
    >
      {/* Main content - responsive padding */}
      <div className="p-3 sm:p-4">
        {/* Header row */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <WorkoutTypeIcon type={workout.type} />
              <h3 className="font-semibold text-gray-100 text-sm sm:text-base truncate">
                {workout.name || getWorkoutTypeLabel(workout.type)}
              </h3>
            </div>
            <div className="flex flex-wrap items-center gap-1 sm:gap-2 text-xs sm:text-sm text-gray-400">
              <span>{formatDate(workout.date)}</span>
              <span className="text-gray-600 hidden sm:inline">|</span>
              <span className="hidden sm:inline">{getRelativeTime(workout.startTime)}</span>
            </div>
          </div>

          <Link
            href={`/workouts/${workout.id}`}
            className="shrink-0 text-xs sm:text-sm text-teal-400 hover:text-teal-300 active:text-teal-200 px-2 py-1 -mr-2 rounded-lg hover:bg-teal-900/20 transition-colors min-h-[36px] sm:min-h-[44px] flex items-center touch-manipulation"
            aria-label={`View details for ${workout.name || getWorkoutTypeLabel(workout.type)}`}
          >
            View
            <span className="hidden sm:inline ml-1">details</span>
          </Link>
        </div>

        {/* Key metrics - responsive grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-3">
          {workout.distance && (
            <MetricItem
              label="Distance"
              value={`${formatDistance(workout.distance)} km`}
            />
          )}
          <MetricItem
            label="Duration"
            value={formatDuration(workout.duration)}
          />
          {workout.metrics.avgPace && (
            <MetricItem
              label="Pace"
              value={`${formatPace(workout.metrics.avgPace)}`}
              unit="/km"
            />
          )}
          {workout.metrics.avgHeartRate && (
            <MetricItem
              label="HR"
              value={`${workout.metrics.avgHeartRate}`}
              unit="bpm"
            />
          )}
        </div>

        {/* HR Zones mini chart */}
        {workout.hrZones && workout.hrZones.length > 0 && (
          <div className="mb-3" role="img" aria-label="Heart rate zone distribution">
            <div className="flex h-2 sm:h-2.5 rounded-full overflow-hidden bg-gray-800">
              {workout.hrZones.map((zone) => (
                <div
                  key={zone.zone}
                  style={{
                    width: `${zone.percentage}%`,
                    backgroundColor: getHRZoneColor(zone.zone),
                  }}
                  title={`${getHRZoneLabel(zone.zone)}: ${zone.percentage.toFixed(0)}%`}
                  aria-label={`${getHRZoneLabel(zone.zone)}: ${zone.percentage.toFixed(0)}%`}
                />
              ))}
            </div>
          </div>
        )}

        {/* Analysis toggle / CTA - responsive */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-3 border-t border-gray-800">
          {hasAnalysis ? (
            <button
              onClick={toggleExpanded}
              className="flex items-center gap-1.5 text-xs sm:text-sm text-gray-400 hover:text-gray-200 active:text-gray-100 px-2 py-2 -ml-2 rounded-lg hover:bg-gray-800 transition-colors min-h-[44px] touch-manipulation"
              aria-expanded={isExpanded}
              aria-controls={`analysis-${workout.id}`}
            >
              <ChevronIcon isOpen={isExpanded} />
              <span>{isExpanded ? 'Hide' : 'Show'} AI Analysis</span>
            </button>
          ) : (
            <button
              onClick={onAnalyze}
              disabled={isAnalyzing}
              className={cn(
                'flex items-center gap-1.5 text-xs sm:text-sm px-3 sm:px-4 py-2 sm:py-2.5 rounded-lg transition-colors min-h-[44px] touch-manipulation',
                isAnalyzing
                  ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                  : 'bg-teal-900/50 text-teal-400 hover:bg-teal-900 active:bg-teal-800'
              )}
              aria-busy={isAnalyzing}
            >
              {isAnalyzing ? (
                <>
                  <LoadingSpinner size="sm" />
                  <span>Analyzing...</span>
                </>
              ) : (
                <>
                  <SparklesIcon />
                  <span className="hidden sm:inline">Generate AI Analysis</span>
                  <span className="sm:hidden">Analyze</span>
                </>
              )}
            </button>
          )}

          {/* Pace splits indicator */}
          {workout.paceSplits && workout.paceSplits.length > 0 && (
            <span className="text-xs text-gray-500 px-2 py-1">
              {workout.paceSplits.length} splits
            </span>
          )}
        </div>
      </div>

      {/* Expanded analysis section */}
      {isExpanded && analysis && (
        <div
          id={`analysis-${workout.id}`}
          className="px-3 sm:px-4 pb-3 sm:pb-4 animate-slideDown"
        >
          <div className="bg-gray-800 rounded-lg p-3 sm:p-4 border border-gray-700">
            <h4 className="font-medium text-gray-100 mb-2 flex items-center gap-1.5 text-sm sm:text-base">
              <SparklesIcon className="text-teal-400" />
              AI Analysis Summary
            </h4>
            <p className="text-xs sm:text-sm text-gray-300 mb-3 leading-relaxed">
              {analysis.summary}
            </p>

            {/* What went well */}
            {analysis.whatWentWell && analysis.whatWentWell.length > 0 && (
              <div className="mb-3">
                <h5 className="text-xs font-medium text-green-400 uppercase tracking-wide mb-1.5">
                  What Went Well
                </h5>
                <ul className="text-xs sm:text-sm text-gray-300 space-y-1.5">
                  {analysis.whatWentWell.slice(0, 2).map((item, index) => (
                    <li key={index} className="flex items-start gap-1.5">
                      <span className="text-green-400 mt-0.5 shrink-0">+</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Improvements */}
            {analysis.improvements && analysis.improvements.length > 0 && (
              <div>
                <h5 className="text-xs font-medium text-amber-400 uppercase tracking-wide mb-1.5">
                  Areas to Improve
                </h5>
                <ul className="text-xs sm:text-sm text-gray-300 space-y-1.5">
                  {analysis.improvements.slice(0, 2).map((item, index) => (
                    <li key={index} className="flex items-start gap-1.5">
                      <span className="text-amber-400 mt-0.5 shrink-0">!</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <Link
              href={`/workouts/${workout.id}`}
              className="inline-flex items-center mt-3 text-xs sm:text-sm text-teal-400 hover:text-teal-300 active:text-teal-200 px-2 py-1 -ml-2 rounded-lg hover:bg-teal-900/20 transition-colors min-h-[44px] touch-manipulation"
            >
              View full analysis
              <svg className="w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </Link>
          </div>
        </div>
      )}
    </article>
  );
}

// Helper components
function MetricItem({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div>
      <dt className="text-xs text-gray-500 uppercase tracking-wide">{label}</dt>
      <dd className="text-sm font-medium text-gray-100">
        {value}{unit && <span className="text-gray-400 text-xs ml-0.5">{unit}</span>}
      </dd>
    </div>
  );
}

function WorkoutTypeIcon({ type }: { type: string }) {
  const iconMap: Record<string, React.ReactElement> = {
    running: (
      <svg className="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
    cycling: (
      <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <circle cx="5" cy="17" r="3" strokeWidth={2} />
        <circle cx="19" cy="17" r="3" strokeWidth={2} />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 17V9l4-4m-8 8h8" />
      </svg>
    ),
    swimming: (
      <svg className="w-5 h-5 text-cyan-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15c2.5 2.5 6 2.5 8.5 0s6-2.5 8.5 0" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 19c2.5 2.5 6 2.5 8.5 0s6-2.5 8.5 0" />
        <circle cx="16" cy="7" r="2" strokeWidth={2} />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 9v2l-4 2" />
      </svg>
    ),
    strength: (
      <svg className="w-5 h-5 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12h4m10 0h4M7 12a2 2 0 104 0 2 2 0 00-4 0zm6 0a2 2 0 104 0 2 2 0 00-4 0z" />
      </svg>
    ),
    hiit: (
      <svg className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z" />
      </svg>
    ),
    yoga: (
      <svg className="w-5 h-5 text-teal-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 2a3 3 0 100 6 3 3 0 000-6zm0 8c-4 0-6 2-6 4v2h12v-2c0-2-2-4-6-4z" />
      </svg>
    ),
    walking: (
      <svg className="w-5 h-5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4a2 2 0 100 4 2 2 0 000-4zm0 6c-1.5 0-2 1-2 2v4l-2 4m4-8v4l2 4" />
      </svg>
    ),
  };

  return iconMap[type] || (
    <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  );
}

function ChevronIcon({ isOpen }: { isOpen: boolean }) {
  return (
    <svg
      className={cn('w-4 h-4 transition-transform duration-200', isOpen && 'rotate-180')}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  );
}

function SparklesIcon({ className }: { className?: string }) {
  return (
    <svg
      className={cn('w-4 h-4', className)}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"
      />
    </svg>
  );
}

function LoadingSpinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizeClasses = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4',
    lg: 'w-6 h-6',
  };

  return (
    <svg
      className={cn('animate-spin', sizeClasses[size])}
      fill="none"
      viewBox="0 0 24 24"
    >
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

export default WorkoutCard;
