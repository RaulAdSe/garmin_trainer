'use client';

import { useState, useCallback, useMemo } from 'react';
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
import { WorkoutScoreBadge } from './WorkoutScoreBadge';

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

  // Calculate score for badge (when analysis exists)
  const overallScore = useMemo(() => {
    if (!analysis) return null;
    if (analysis.overallScore) return analysis.overallScore;
    // Fallback: derive from execution rating
    const ratingScores: Record<string, number> = {
      excellent: 92,
      good: 78,
      fair: 55,
      needs_improvement: 35,
    };
    return analysis.executionRating ? ratingScores[analysis.executionRating] || 70 : 70;
  }, [analysis]);

  // Build score breakdown for tooltip
  const scoreBreakdown = useMemo(() => {
    if (!analysis) return undefined;
    return {
      execution: analysis.executionRating || null,
      trainingEffect: analysis.trainingEffectScore ?? workout.metrics?.trainingEffect ?? null,
      load: analysis.loadScore ?? null,
    };
  }, [analysis, workout]);

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
            <div className="flex items-center gap-3">
              <button
                onClick={toggleExpanded}
                className="flex items-center gap-1.5 text-xs sm:text-sm text-gray-400 hover:text-gray-200 active:text-gray-100 px-2 py-2 -ml-2 rounded-lg hover:bg-gray-800 transition-colors min-h-[44px] touch-manipulation"
                aria-expanded={isExpanded}
                aria-controls={`analysis-${workout.id}`}
              >
                <ChevronIcon isOpen={isExpanded} />
                <span>{isExpanded ? 'Hide' : 'Show'} AI Analysis</span>
              </button>
              {/* Score badge - always visible */}
              {overallScore !== null && (
                <WorkoutScoreBadge
                  score={overallScore}
                  breakdown={scoreBreakdown}
                  size="sm"
                />
              )}
            </div>
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
    // Running variants
    running: (
      <svg className="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <circle cx="12" cy="4" r="2" strokeWidth={2} />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7l-3 3-2-1-4 4m0 0l2 5m-2-5l-3 1m10-4l3 8m-1-4h3" />
      </svg>
    ),
    trail_running: (
      <svg className="w-5 h-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 20l4-4 4 2 4-6 4 4" />
        <circle cx="14" cy="6" r="2" strokeWidth={2} />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 8l-2 2-2-1" />
      </svg>
    ),
    // Cycling
    cycling: (
      <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <circle cx="5" cy="17" r="3" strokeWidth={2} />
        <circle cx="19" cy="17" r="3" strokeWidth={2} />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 17V9l4-4m-8 8h8" />
      </svg>
    ),
    // Swimming
    swimming: (
      <svg className="w-5 h-5 text-cyan-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15c2.5 2.5 6 2.5 8.5 0s6-2.5 8.5 0" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 19c2.5 2.5 6 2.5 8.5 0s6-2.5 8.5 0" />
        <circle cx="16" cy="7" r="2" strokeWidth={2} />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 9v2l-4 2" />
      </svg>
    ),
    // Walking
    walking: (
      <svg className="w-5 h-5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <circle cx="12" cy="4" r="2" strokeWidth={2} />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10l-2 6-2-2-2 6m4-10v4m2-4l2 2" />
      </svg>
    ),
    // Hiking
    hiking: (
      <svg className="w-5 h-5 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 20l4-4 4 2 4-6 4 4" />
        <circle cx="12" cy="6" r="2" strokeWidth={2} />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m-2 8l2-4 2 4" />
      </svg>
    ),
    // Strength
    strength: (
      <svg className="w-5 h-5 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12h4m10 0h4M7 12a2 2 0 104 0 2 2 0 00-4 0zm6 0a2 2 0 104 0 2 2 0 00-4 0z" />
      </svg>
    ),
    // HIIT
    hiit: (
      <svg className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z" />
      </svg>
    ),
    // Yoga
    yoga: (
      <svg className="w-5 h-5 text-teal-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <circle cx="12" cy="4" r="2" strokeWidth={2} />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v4m-4 2h8m-8 0l-2 4m10-4l2 4m-6 0v4" />
      </svg>
    ),
    // Skiing / Winter Sports
    skiing: (
      <svg className="w-5 h-5 text-sky-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <circle cx="14" cy="4" r="2" strokeWidth={2} />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 18l18-6M10 10l4 4-2 4m-2-8l-4 1" />
      </svg>
    ),
    // Football / Soccer
    football: (
      <svg className="w-5 h-5 text-lime-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <circle cx="12" cy="12" r="9" strokeWidth={2} />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v4m0 10v4M3 12h4m10 0h4m-9-5l3 2v4l-3 2-3-2v-4l3-2z" />
      </svg>
    ),
    // Tennis / Racket Sports
    tennis: (
      <svg className="w-5 h-5 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <circle cx="15" cy="9" r="6" strokeWidth={2} />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l-6 6m0 0l2-2m-2 2l-2-2" />
      </svg>
    ),
    // Basketball / Team Sports
    basketball: (
      <svg className="w-5 h-5 text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <circle cx="12" cy="12" r="9" strokeWidth={2} />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v18M3 12c0-3 4-5 9-5s9 2 9 5" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12c0 3 4 5 9 5s9-2 9-5" />
      </svg>
    ),
    // Golf
    golf: (
      <svg className="w-5 h-5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v14m0-14l6 4-6 4m-4 10h8" />
        <circle cx="12" cy="20" r="1" fill="currentColor" />
      </svg>
    ),
    // Rowing / Paddle Sports
    rowing: (
      <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 17h18M6 14l3-6 6 4 3-4" />
        <ellipse cx="12" cy="17" rx="6" ry="2" strokeWidth={2} />
      </svg>
    ),
    // Surfing
    surfing: (
      <svg className="w-5 h-5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 17c2 2 4 2 6 0s4-2 6 0 4 2 6 0" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12l4-8 4 8H8z" />
        <circle cx="12" cy="6" r="1" fill="currentColor" />
      </svg>
    ),
    // Elliptical / Cardio Machine
    elliptical: (
      <svg className="w-5 h-5 text-pink-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <ellipse cx="12" cy="12" rx="8" ry="4" strokeWidth={2} />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v8m-4-4h8" />
      </svg>
    ),
    // Climbing
    climbing: (
      <svg className="w-5 h-5 text-stone-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 20l4-16 4 16" />
        <circle cx="8" cy="8" r="1" fill="currentColor" />
        <circle cx="16" cy="12" r="1" fill="currentColor" />
        <circle cx="10" cy="16" r="1" fill="currentColor" />
      </svg>
    ),
    // Martial Arts
    martial_arts: (
      <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <circle cx="12" cy="4" r="2" strokeWidth={2} />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 8l4 2 4-2m-8 4l4 1 4-1m-6 4l2 4m4-4l2 4" />
      </svg>
    ),
    // Skating
    skating: (
      <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <circle cx="10" cy="5" r="2" strokeWidth={2} />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 8l-4 4 2 4h4M6 20h12M8 20l2-4" />
      </svg>
    ),
    // Dance
    dance: (
      <svg className="w-5 h-5 text-fuchsia-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <circle cx="12" cy="4" r="2" strokeWidth={2} />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 8l3 2 3-2m-6 4l3 1 3-1m-5 4l2 4m4-4l2 4" />
      </svg>
    ),
    // Triathlon
    triathlon: (
      <svg className="w-5 h-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <circle cx="6" cy="12" r="3" strokeWidth={2} />
        <circle cx="12" cy="12" r="3" strokeWidth={2} />
        <circle cx="18" cy="12" r="3" strokeWidth={2} />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6 9v-1m6-1v-2m6 3v-1" />
      </svg>
    ),
  };

  // Return the mapped icon or a generic activity icon
  return iconMap[type] || (
    <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <circle cx="12" cy="12" r="9" strokeWidth={2} />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l2 2" />
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
