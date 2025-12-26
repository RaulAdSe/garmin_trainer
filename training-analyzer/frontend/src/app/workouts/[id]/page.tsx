'use client';

import { use } from 'react';
import Link from 'next/link';
import { useWorkout, useWorkoutAnalysis } from '@/hooks/useWorkouts';
import { useLLMStream } from '@/hooks/useLLMStream';
import { WorkoutAnalysis, WorkoutAnalysisSkeleton } from '@/components/workouts/WorkoutAnalysis';
import { StreamingAnalysis } from '@/components/workouts/StreamingAnalysis';
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

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column - Workout details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Key metrics */}
          <section className="bg-gray-900 rounded-lg border border-gray-800 p-6">
            <h2 className="text-lg font-semibold text-gray-100 mb-4">
              Workout Summary
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
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
              {workout.metrics.avgPace && (
                <MetricCard
                  label="Avg Pace"
                  value={`${formatPace(workout.metrics.avgPace)} /km`}
                  icon={<PaceIcon />}
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
                  label="Elevation Gain"
                  value={`${workout.metrics.elevationGain} m`}
                  icon={<ElevationIcon />}
                />
              )}
              {workout.metrics.avgCadence && (
                <MetricCard
                  label="Avg Cadence"
                  value={`${workout.metrics.avgCadence} spm`}
                  icon={<CadenceIcon />}
                />
              )}
            </div>
          </section>

          {/* HR Zones */}
          {workout.hrZones && workout.hrZones.length > 0 && (
            <section className="bg-gray-900 rounded-lg border border-gray-800 p-6">
              <h2 className="text-lg font-semibold text-gray-100 mb-4">
                Heart Rate Zones
              </h2>
              <div className="space-y-3">
                {workout.hrZones.map((zone) => (
                  <div key={zone.zone} className="flex items-center gap-4">
                    <div className="w-20 text-sm font-medium text-gray-300">
                      {getHRZoneLabel(zone.zone)}
                    </div>
                    <div className="flex-1">
                      <div className="h-6 bg-gray-800 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${zone.percentage}%`,
                            backgroundColor: getHRZoneColor(zone.zone),
                          }}
                        />
                      </div>
                    </div>
                    <div className="w-16 text-right text-sm text-gray-400">
                      {zone.percentage.toFixed(1)}%
                    </div>
                    <div className="w-20 text-right text-sm text-gray-500">
                      {formatDuration(zone.duration)}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Pace Splits */}
          {workout.paceSplits && workout.paceSplits.length > 0 && (
            <section className="bg-gray-900 rounded-lg border border-gray-800 p-6">
              <h2 className="text-lg font-semibold text-gray-100 mb-4">
                Pace Splits
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-800">
                      <th className="text-left py-2 text-gray-500 font-medium">Split</th>
                      <th className="text-right py-2 text-gray-500 font-medium">Distance</th>
                      <th className="text-right py-2 text-gray-500 font-medium">Time</th>
                      <th className="text-right py-2 text-gray-500 font-medium">Pace</th>
                      {workout.paceSplits[0].avgHR && (
                        <th className="text-right py-2 text-gray-500 font-medium">Avg HR</th>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {workout.paceSplits.map((split) => (
                      <tr key={split.splitNumber} className="border-b border-gray-800">
                        <td className="py-2 text-gray-100">
                          {split.splitNumber}
                        </td>
                        <td className="py-2 text-right text-gray-300">
                          {formatDistance(split.distance, 2)} km
                        </td>
                        <td className="py-2 text-right text-gray-300">
                          {formatDuration(split.duration)}
                        </td>
                        <td className="py-2 text-right text-teal-400 font-medium">
                          {formatPace(split.pace)} /km
                        </td>
                        {split.avgHR && (
                          <td className="py-2 text-right text-gray-300">
                            {split.avgHR} bpm
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Notes */}
          {workout.notes && (
            <section className="bg-gray-900 rounded-lg border border-gray-800 p-6">
              <h2 className="text-lg font-semibold text-gray-100 mb-4">
                Notes
              </h2>
              <p className="text-gray-300 whitespace-pre-wrap">{workout.notes}</p>
            </section>
          )}
        </div>

        {/* Right column - AI Analysis */}
        <div className="space-y-6">
          <section className="bg-gray-900 rounded-lg border border-gray-800 p-6">
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
  const icons: Record<string, React.ReactElement> = {
    running: (
      <div className="p-2 bg-blue-900/50 rounded-lg">
        <svg className="w-6 h-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      </div>
    ),
    cycling: (
      <div className="p-2 bg-green-900/50 rounded-lg">
        <svg className="w-6 h-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <circle cx="5" cy="17" r="3" strokeWidth={2} />
          <circle cx="19" cy="17" r="3" strokeWidth={2} />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 17V9l4-4m-8 8h8" />
        </svg>
      </div>
    ),
  };

  return icons[type] || (
    <div className="p-2 bg-gray-800 rounded-lg">
      <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
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
