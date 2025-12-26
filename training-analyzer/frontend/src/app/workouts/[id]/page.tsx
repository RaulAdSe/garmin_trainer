'use client';

import { use, useState, useEffect } from 'react';
import Link from 'next/link';
import { useWorkout, useWorkoutAnalysis } from '@/hooks/useWorkouts';
import { useLLMStream } from '@/hooks/useLLMStream';
import { WorkoutAnalysis, WorkoutAnalysisSkeleton } from '@/components/workouts/WorkoutAnalysis';
import { StreamingAnalysis } from '@/components/workouts/StreamingAnalysis';
import { WorkoutCharts } from '@/components/workout-detail/WorkoutCharts';
import { RouteMap } from '@/components/workout-detail/RouteMap';
import { SplitsTable } from '@/components/workout-detail/SplitsTable';
import { getActivityDetails } from '@/lib/api-client';
import type { ActivityDetailsResponse } from '@/types/workout-detail';
import {
  cn,
  formatDuration,
  formatPace,
  formatDistance,
  formatDate,
  formatTime,
  getWorkoutTypeLabel,
  getHRZoneColor,
  getHRZoneLabel,
} from '@/lib/utils';

interface WorkoutDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function WorkoutDetailPage({ params }: WorkoutDetailPageProps) {
  const { id: workoutId } = use(params);

  const { workout, isLoading: isLoadingWorkout, isError, error } = useWorkout(workoutId);
  const {
    analysis,
    isLoading: isLoadingAnalysis,
    analyze,
    isAnalyzing,
  } = useWorkoutAnalysis(workoutId);

  const {
    content: streamContent,
    isStreaming,
    isComplete,
    error: streamError,
    startStream,
  } = useLLMStream({
    onComplete: () => {
      // Refetch analysis when stream completes
    },
  });

  // Activity details state (time series, GPS, splits)
  const [activityDetails, setActivityDetails] = useState<ActivityDetailsResponse | null>(null);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [detailsError, setDetailsError] = useState<string | null>(null);

  // Synchronized hover state for charts and map
  const [activeHoverIndex, setActiveHoverIndex] = useState<number | null>(null);

  // Fetch activity details when workout is loaded
  useEffect(() => {
    if (!workout) return;

    const fetchDetails = async () => {
      setIsLoadingDetails(true);
      setDetailsError(null);
      try {
        const details = await getActivityDetails(workoutId);
        setActivityDetails(details);
      } catch (err) {
        console.error('Failed to fetch activity details:', err);
        setDetailsError(err instanceof Error ? err.message : 'Failed to load activity details');
      } finally {
        setIsLoadingDetails(false);
      }
    };

    fetchDetails();
  }, [workout, workoutId]);

  // Determine if this is a running activity (for pace vs speed display)
  const isRunning = activityDetails?.is_running ??
    ['running', 'trail_running', 'walking', 'hiking'].includes(workout?.type || '');

  const handleAnalyze = async (regenerate = false) => {
    if (regenerate || !analysis) {
      startStream(workoutId, regenerate);
    }
  };

  if (isLoadingWorkout) {
    return <WorkoutDetailSkeleton />;
  }

  if (isError || !workout) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-8 max-w-md text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-red-900/50 rounded-full mb-4">
            <ErrorIcon className="w-6 h-6 text-red-400" />
          </div>
          <h2 className="text-lg font-semibold text-gray-100 mb-2">
            Workout Not Found
          </h2>
          <p className="text-sm text-gray-400 mb-4">
            {error?.message || "The workout you're looking for doesn't exist or has been deleted."}
          </p>
          <Link
            href="/workouts"
            className="inline-flex items-center gap-2 px-4 py-2 bg-teal-600 text-white rounded-md text-sm hover:bg-teal-700 transition-colors"
          >
            <BackIcon />
            Back to Workouts
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/workouts"
          className="inline-flex items-center gap-1 text-sm text-gray-400 hover:text-gray-200 mb-4"
        >
          <BackIcon />
          Back to Workouts
        </Link>

        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <WorkoutTypeIcon type={workout.type} />
              <h1 className="text-2xl font-bold text-gray-100">
                {workout.name || getWorkoutTypeLabel(workout.type)}
              </h1>
            </div>
            <div className="flex items-center gap-3 text-sm text-gray-400">
              <span>{formatDate(workout.date)}</span>
              <span className="text-gray-600">|</span>
              <span>{formatTime(workout.startTime)}</span>
              <span className="text-gray-600">|</span>
              <span className="capitalize">{workout.source}</span>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            {analysis && !isStreaming && (
              <button
                onClick={() => handleAnalyze(true)}
                disabled={isAnalyzing}
                className="px-3 py-1.5 text-sm text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded-md transition-colors"
              >
                Regenerate Analysis
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Main content - Full width for charts and map */}
      <div className="space-y-6">
        {/* Key metrics - compact row */}
        <section className="bg-gray-900 rounded-xl border border-gray-800 p-4 sm:p-6">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 sm:gap-6">
            {workout.distance && (
              <MetricCard
                label="Distance"
                value={`${formatDistance(workout.distance)} km`}
                icon={<DistanceIcon />}
              />
            )}
            <MetricCard
              label="Duration"
              value={formatDuration(workout.duration)}
              icon={<DurationIcon />}
            />
            {isRunning && workout.metrics.avgPace && (
              <MetricCard
                label="Avg Pace"
                value={`${formatPace(workout.metrics.avgPace)} /km`}
                icon={<PaceIcon />}
              />
            )}
            {!isRunning && workout.metrics.avgPace && workout.metrics.avgPace > 0 && (
              <MetricCard
                label="Avg Speed"
                value={`${(60 / workout.metrics.avgPace).toFixed(1)} km/h`}
                icon={<SpeedIcon />}
              />
            )}
            {workout.metrics.avgHeartRate && (
              <MetricCard
                label="Avg HR"
                value={`${workout.metrics.avgHeartRate} bpm`}
                icon={<HeartIcon />}
              />
            )}
            {workout.metrics.maxHeartRate && (
              <MetricCard
                label="Max HR"
                value={`${workout.metrics.maxHeartRate} bpm`}
                icon={<HeartIcon />}
              />
            )}
            {workout.metrics.calories && (
              <MetricCard
                label="Calories"
                value={`${workout.metrics.calories}`}
                icon={<CaloriesIcon />}
              />
            )}
            {workout.metrics.elevationGain && (
              <MetricCard
                label="Elevation"
                value={`${workout.metrics.elevationGain} m`}
                icon={<ElevationIcon />}
              />
            )}
            {workout.metrics.avgCadence && (
              <MetricCard
                label="Cadence"
                value={`${workout.metrics.avgCadence} spm`}
                icon={<CadenceIcon />}
              />
            )}
          </div>
        </section>

        {/* Route Map + AI Analysis side by side */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Route Map - Left side (3/5 width) */}
          <div className="lg:col-span-3">
            {isLoadingDetails ? (
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 h-[500px] animate-pulse">
                <div className="h-6 bg-gray-800 rounded w-32 mb-4"></div>
                <div className="h-full bg-gray-800 rounded"></div>
              </div>
            ) : activityDetails ? (
              <RouteMap
                gpsData={activityDetails.gps_coordinates}
                activeIndex={activeHoverIndex}
                chartDataLength={400}
                onHoverIndex={setActiveHoverIndex}
              />
            ) : detailsError ? (
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 h-[500px] flex items-center justify-center">
                <p className="text-gray-400">{detailsError}</p>
              </div>
            ) : null}
          </div>

          {/* AI Analysis - Right side (2/5 width) */}
          <div className="lg:col-span-2">
            <section className="bg-gray-900 rounded-xl border border-gray-800 p-6 h-full">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-100 flex items-center gap-2">
                  <SparklesIcon className="text-teal-400" />
                  AI Analysis
                </h2>
              </div>

              {isStreaming || streamContent ? (
                <StreamingAnalysis
                  content={streamContent}
                  isStreaming={isStreaming}
                  isComplete={isComplete}
                  error={streamError}
                />
              ) : isLoadingAnalysis ? (
                <WorkoutAnalysisSkeleton />
              ) : analysis ? (
                <WorkoutAnalysis analysis={analysis} workout={workout} />
              ) : (
                <div className="text-center py-8">
                  <div className="inline-flex items-center justify-center w-12 h-12 bg-teal-900/50 rounded-full mb-4">
                    <SparklesIcon className="w-6 h-6 text-teal-400" />
                  </div>
                  <h3 className="text-sm font-medium text-gray-100 mb-2">
                    No Analysis Yet
                  </h3>
                  <p className="text-sm text-gray-400 mb-4">
                    Get AI-powered insights about your workout performance.
                  </p>
                  <button
                    onClick={() => handleAnalyze()}
                    disabled={isAnalyzing}
                    className={cn(
                      'inline-flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
                      isAnalyzing
                        ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                        : 'bg-teal-600 text-white hover:bg-teal-700'
                    )}
                  >
                    {isAnalyzing ? (
                      <>
                        <LoadingSpinner />
                        Analyzing...
                      </>
                    ) : (
                      <>
                        <SparklesIcon className="w-4 h-4" />
                        Generate Analysis
                      </>
                    )}
                  </button>
                </div>
              )}
            </section>
          </div>
        </div>

        {/* Interactive Charts - Full width */}
        {activityDetails && (
          <WorkoutCharts
            timeSeries={activityDetails.time_series}
            isRunning={isRunning}
            activeIndex={activeHoverIndex}
            onHoverIndexChange={setActiveHoverIndex}
          />
        )}

        {/* Splits Table */}
        {activityDetails?.splits && activityDetails.splits.length > 0 && (
          <SplitsTable
            splits={activityDetails.splits}
            isRunning={isRunning}
          />
        )}

        {/* HR Zones and Notes */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* HR Zones */}
          {workout.hrZones && workout.hrZones.length > 0 && (
            <section className="bg-gray-900 rounded-xl border border-gray-800 p-4 sm:p-6">
              <h2 className="text-lg font-semibold text-gray-100 mb-4">
                Heart Rate Zones
              </h2>
              <div className="space-y-3">
                {workout.hrZones.map((zone) => (
                  <div key={zone.zone} className="flex items-center gap-3 sm:gap-4">
                    <div className="w-16 sm:w-20 text-sm font-medium text-gray-300">
                      {getHRZoneLabel(zone.zone)}
                    </div>
                    <div className="flex-1">
                      <div className="h-5 sm:h-6 bg-gray-800 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${zone.percentage}%`,
                            backgroundColor: getHRZoneColor(zone.zone),
                          }}
                        />
                      </div>
                    </div>
                    <div className="w-12 sm:w-16 text-right text-sm text-gray-400">
                      {zone.percentage.toFixed(1)}%
                    </div>
                    <div className="hidden sm:block w-20 text-right text-sm text-gray-500">
                      {formatDuration(zone.duration)}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Notes */}
          {workout.notes && (
            <section className="bg-gray-900 rounded-xl border border-gray-800 p-4 sm:p-6">
              <h2 className="text-lg font-semibold text-gray-100 mb-4">
                Notes
              </h2>
              <p className="text-gray-300 whitespace-pre-wrap">{workout.notes}</p>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}

// Helper components
function MetricCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="p-2 bg-gray-800 rounded-lg text-gray-400">{icon}</div>
      <div>
        <dt className="text-xs text-gray-500 uppercase tracking-wide">{label}</dt>
        <dd className="text-lg font-semibold text-gray-100">{value}</dd>
      </div>
    </div>
  );
}

function WorkoutDetailSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div>
        <div className="w-32 h-4 bg-gray-800 rounded mb-4" />
        <div className="w-64 h-8 bg-gray-800 rounded mb-2" />
        <div className="w-48 h-4 bg-gray-700 rounded" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-6 h-48" />
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-6 h-64" />
        </div>
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-6 h-96" />
      </div>
    </div>
  );
}

// Icon components
function BackIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
    </svg>
  );
}

function ErrorIcon({ className }: { className?: string }) {
  return (
    <svg className={cn('w-5 h-5', className)} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function SparklesIcon({ className }: { className?: string }) {
  return (
    <svg className={cn('w-5 h-5', className)} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"
      />
    </svg>
  );
}

function WorkoutTypeIcon({ type }: { type: string }) {
  const iconConfig: Record<string, { bg: string; color: string; icon: React.ReactElement }> = {
    // Running variants
    running: {
      bg: 'bg-blue-900/50',
      color: 'text-blue-400',
      icon: (
        <>
          <circle cx="12" cy="4" r="2" strokeWidth={2} />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7l-3 3-2-1-4 4m0 0l2 5m-2-5l-3 1m10-4l3 8m-1-4h3" />
        </>
      ),
    },
    trail_running: {
      bg: 'bg-emerald-900/50',
      color: 'text-emerald-400',
      icon: (
        <>
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 20l4-4 4 2 4-6 4 4" />
          <circle cx="14" cy="6" r="2" strokeWidth={2} />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 8l-2 2-2-1" />
        </>
      ),
    },
    // Cycling
    cycling: {
      bg: 'bg-green-900/50',
      color: 'text-green-400',
      icon: (
        <>
          <circle cx="5" cy="17" r="3" strokeWidth={2} />
          <circle cx="19" cy="17" r="3" strokeWidth={2} />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 17V9l4-4m-8 8h8" />
        </>
      ),
    },
    // Swimming
    swimming: {
      bg: 'bg-cyan-900/50',
      color: 'text-cyan-400',
      icon: (
        <>
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15c2.5 2.5 6 2.5 8.5 0s6-2.5 8.5 0" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 19c2.5 2.5 6 2.5 8.5 0s6-2.5 8.5 0" />
          <circle cx="16" cy="7" r="2" strokeWidth={2} />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 9v2l-4 2" />
        </>
      ),
    },
    // Walking
    walking: {
      bg: 'bg-amber-900/50',
      color: 'text-amber-400',
      icon: (
        <>
          <circle cx="12" cy="4" r="2" strokeWidth={2} />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10l-2 6-2-2-2 6m4-10v4m2-4l2 2" />
        </>
      ),
    },
    // Hiking
    hiking: {
      bg: 'bg-orange-900/50',
      color: 'text-orange-400',
      icon: (
        <>
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 20l4-4 4 2 4-6 4 4" />
          <circle cx="12" cy="6" r="2" strokeWidth={2} />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m-2 8l2-4 2 4" />
        </>
      ),
    },
    // Strength
    strength: {
      bg: 'bg-purple-900/50',
      color: 'text-purple-400',
      icon: (
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12h4m10 0h4M7 12a2 2 0 104 0 2 2 0 00-4 0zm6 0a2 2 0 104 0 2 2 0 00-4 0z" />
      ),
    },
    // HIIT
    hiit: {
      bg: 'bg-red-900/50',
      color: 'text-red-400',
      icon: (
        <>
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z" />
        </>
      ),
    },
    // Yoga
    yoga: {
      bg: 'bg-teal-900/50',
      color: 'text-teal-400',
      icon: (
        <>
          <circle cx="12" cy="4" r="2" strokeWidth={2} />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v4m-4 2h8m-8 0l-2 4m10-4l2 4m-6 0v4" />
        </>
      ),
    },
    // Skiing
    skiing: {
      bg: 'bg-sky-900/50',
      color: 'text-sky-400',
      icon: (
        <>
          <circle cx="14" cy="4" r="2" strokeWidth={2} />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 18l18-6M10 10l4 4-2 4m-2-8l-4 1" />
        </>
      ),
    },
    // Football
    football: {
      bg: 'bg-lime-900/50',
      color: 'text-lime-400',
      icon: (
        <>
          <circle cx="12" cy="12" r="9" strokeWidth={2} />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v4m0 10v4M3 12h4m10 0h4m-9-5l3 2v4l-3 2-3-2v-4l3-2z" />
        </>
      ),
    },
    // Tennis
    tennis: {
      bg: 'bg-yellow-900/50',
      color: 'text-yellow-400',
      icon: (
        <>
          <circle cx="15" cy="9" r="6" strokeWidth={2} />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l-6 6m0 0l2-2m-2 2l-2-2" />
        </>
      ),
    },
    // Basketball
    basketball: {
      bg: 'bg-orange-900/50',
      color: 'text-orange-300',
      icon: (
        <>
          <circle cx="12" cy="12" r="9" strokeWidth={2} />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v18M3 12c0-3 4-5 9-5s9 2 9 5" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12c0 3 4 5 9 5s9-2 9-5" />
        </>
      ),
    },
    // Golf
    golf: {
      bg: 'bg-green-900/50',
      color: 'text-green-300',
      icon: (
        <>
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v14m0-14l6 4-6 4m-4 10h8" />
          <circle cx="12" cy="20" r="1" fill="currentColor" />
        </>
      ),
    },
    // Rowing
    rowing: {
      bg: 'bg-blue-900/50',
      color: 'text-blue-300',
      icon: (
        <>
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 17h18M6 14l3-6 6 4 3-4" />
          <ellipse cx="12" cy="17" rx="6" ry="2" strokeWidth={2} />
        </>
      ),
    },
    // Surfing
    surfing: {
      bg: 'bg-cyan-900/50',
      color: 'text-cyan-300',
      icon: (
        <>
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 17c2 2 4 2 6 0s4-2 6 0 4 2 6 0" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12l4-8 4 8H8z" />
          <circle cx="12" cy="6" r="1" fill="currentColor" />
        </>
      ),
    },
    // Elliptical
    elliptical: {
      bg: 'bg-pink-900/50',
      color: 'text-pink-400',
      icon: (
        <>
          <ellipse cx="12" cy="12" rx="8" ry="4" strokeWidth={2} />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v8m-4-4h8" />
        </>
      ),
    },
    // Climbing
    climbing: {
      bg: 'bg-stone-800/50',
      color: 'text-stone-400',
      icon: (
        <>
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 20l4-16 4 16" />
          <circle cx="8" cy="8" r="1" fill="currentColor" />
          <circle cx="16" cy="12" r="1" fill="currentColor" />
          <circle cx="10" cy="16" r="1" fill="currentColor" />
        </>
      ),
    },
    // Martial Arts
    martial_arts: {
      bg: 'bg-red-900/50',
      color: 'text-red-300',
      icon: (
        <>
          <circle cx="12" cy="4" r="2" strokeWidth={2} />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 8l4 2 4-2m-8 4l4 1 4-1m-6 4l2 4m4-4l2 4" />
        </>
      ),
    },
    // Skating
    skating: {
      bg: 'bg-indigo-900/50',
      color: 'text-indigo-400',
      icon: (
        <>
          <circle cx="10" cy="5" r="2" strokeWidth={2} />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 8l-4 4 2 4h4M6 20h12M8 20l2-4" />
        </>
      ),
    },
    // Dance
    dance: {
      bg: 'bg-fuchsia-900/50',
      color: 'text-fuchsia-400',
      icon: (
        <>
          <circle cx="12" cy="4" r="2" strokeWidth={2} />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 8l3 2 3-2m-6 4l3 1 3-1m-5 4l2 4m4-4l2 4" />
        </>
      ),
    },
    // Triathlon
    triathlon: {
      bg: 'bg-amber-900/50',
      color: 'text-amber-400',
      icon: (
        <>
          <circle cx="6" cy="12" r="3" strokeWidth={2} />
          <circle cx="12" cy="12" r="3" strokeWidth={2} />
          <circle cx="18" cy="12" r="3" strokeWidth={2} />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6 9v-1m6-1v-2m6 3v-1" />
        </>
      ),
    },
  };

  const config = iconConfig[type] || {
    bg: 'bg-gray-800',
    color: 'text-gray-400',
    icon: (
      <>
        <circle cx="12" cy="12" r="9" strokeWidth={2} />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l2 2" />
      </>
    ),
  };

  return (
    <div className={`p-2 ${config.bg} rounded-lg`}>
      <svg className={`w-6 h-6 ${config.color}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
        {config.icon}
      </svg>
    </div>
  );
}

function DistanceIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
    </svg>
  );
}

function DurationIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

function PaceIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  );
}

function SpeedIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 12l4-2" />
    </svg>
  );
}

function HeartIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
      />
    </svg>
  );
}

function CaloriesIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z"
      />
    </svg>
  );
}

function ElevationIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
    </svg>
  );
}

function CadenceIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
    </svg>
  );
}

function LoadingSpinner() {
  return (
    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}
