'use client';

import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import { useRunWalkTimer } from '@/hooks/useRunWalkTimer';
import type { RunWalkInterval, RunWalkPhase } from '@/lib/types';

interface RunWalkTimerProps {
  intervals: RunWalkInterval;
  onComplete?: (totalDuration: number) => void;
  onStop?: () => void;
  className?: string;
}

function formatTimeDisplay(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatTimeLong(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins === 0) return `${secs} seconds`;
  if (secs === 0) return `${mins} minute${mins > 1 ? 's' : ''}`;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Circular progress component
function CircularProgress({
  progress,
  size = 280,
  strokeWidth = 12,
  color,
  children,
}: {
  progress: number;
  size?: number;
  strokeWidth?: number;
  color: string;
  children?: React.ReactNode;
}) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (progress / 100) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-gray-800"
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-300 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        {children}
      </div>
    </div>
  );
}

// Phase indicator badge
function PhaseIndicator({
  phase,
  isPulsing,
}: {
  phase: RunWalkPhase;
  isPulsing: boolean;
}) {
  const t = useTranslations('runWalk');

  const phaseConfig = {
    run: {
      label: t('run'),
      bgClass: 'bg-green-500',
      textClass: 'text-green-400',
      icon: (
        <svg
          className="w-6 h-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13 10V3L4 14h7v7l9-11h-7z"
          />
        </svg>
      ),
    },
    walk: {
      label: t('walk'),
      bgClass: 'bg-blue-500',
      textClass: 'text-blue-400',
      icon: (
        <svg
          className="w-6 h-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M17 8l4 4m0 0l-4 4m4-4H3"
          />
        </svg>
      ),
    },
    idle: {
      label: t('ready'),
      bgClass: 'bg-gray-500',
      textClass: 'text-gray-400',
      icon: (
        <svg
          className="w-6 h-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      ),
    },
  };

  const config = phaseConfig[phase];

  return (
    <div
      className={cn(
        'inline-flex items-center gap-2 px-4 py-2 rounded-full',
        config.bgClass,
        'text-white font-bold text-lg uppercase tracking-wider',
        isPulsing && 'animate-pulse'
      )}
    >
      {config.icon}
      <span>{config.label}</span>
    </div>
  );
}

// Control button
function ControlButton({
  onClick,
  disabled,
  variant,
  children,
}: {
  onClick: () => void;
  disabled?: boolean;
  variant: 'primary' | 'secondary' | 'danger';
  children: React.ReactNode;
}) {
  const variantClasses = {
    primary: 'bg-teal-500 hover:bg-teal-400 text-white',
    secondary: 'bg-gray-700 hover:bg-gray-600 text-white',
    danger: 'bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/30',
  };

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-semibold',
        'transition-all duration-200',
        'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-900',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        variantClasses[variant]
      )}
    >
      {children}
    </button>
  );
}

export function RunWalkTimer({
  intervals,
  onComplete,
  onStop,
  className,
}: RunWalkTimerProps) {
  const t = useTranslations('runWalk');
  const [showConfirmStop, setShowConfirmStop] = useState(false);

  const handleIntervalComplete = useCallback(
    (intervalNumber: number, phase: RunWalkPhase) => {
      console.log(`Interval ${intervalNumber} (${phase}) complete`);
    },
    []
  );

  const handleWorkoutComplete = useCallback(
    (totalDuration: number) => {
      onComplete?.(totalDuration);
    },
    [onComplete]
  );

  const handlePhaseChange = useCallback(
    (newPhase: RunWalkPhase, intervalNumber: number) => {
      console.log(`Phase changed to ${newPhase} at interval ${intervalNumber}`);
    },
    []
  );

  const {
    state,
    start,
    pause,
    resume,
    stop,
    reset,
    skipToNext,
    totalWorkoutDuration,
    formattedTimeRemaining,
    formattedTotalElapsed,
    progressPercent,
    intervalProgressPercent,
  } = useRunWalkTimer({
    intervals,
    onIntervalComplete: handleIntervalComplete,
    onWorkoutComplete: handleWorkoutComplete,
    onPhaseChange: handlePhaseChange,
  });

  // Handle stop confirmation
  const handleStopClick = useCallback(() => {
    if (state.isRunning) {
      setShowConfirmStop(true);
    }
  }, [state.isRunning]);

  const confirmStop = useCallback(() => {
    stop();
    setShowConfirmStop(false);
    onStop?.();
  }, [stop, onStop]);

  // Color based on phase
  const phaseColor =
    state.phase === 'run'
      ? '#22c55e'
      : state.phase === 'walk'
        ? '#3b82f6'
        : '#6b7280';

  // Keep screen awake during workout
  useEffect(() => {
    let wakeLock: WakeLockSentinel | null = null;

    const requestWakeLock = async () => {
      if (state.isRunning && 'wakeLock' in navigator) {
        try {
          wakeLock = await navigator.wakeLock.request('screen');
        } catch {
          // Wake lock not available
        }
      }
    };

    if (state.isRunning) {
      requestWakeLock();
    }

    return () => {
      if (wakeLock) {
        wakeLock.release();
      }
    };
  }, [state.isRunning]);

  return (
    <div className={cn('flex flex-col items-center', className)}>
      {/* Not started state */}
      {!state.isRunning && !state.isComplete && state.phase === 'idle' && (
        <div className="text-center space-y-8">
          <div>
            <h2 className="text-2xl font-bold text-white">{t('getReady')}</h2>
            <p className="mt-2 text-gray-400">
              {t('workoutSummary', {
                run: formatTimeLong(intervals.runSeconds),
                walk: formatTimeLong(intervals.walkSeconds),
                reps: intervals.repetitions,
              })}
            </p>
          </div>

          <div className="text-center">
            <div className="text-5xl font-bold text-white">
              {Math.round(totalWorkoutDuration / 60)}
            </div>
            <div className="text-sm text-gray-500">{t('minutesTotal')}</div>
          </div>

          <button
            type="button"
            onClick={start}
            className={cn(
              'w-full max-w-xs mx-auto py-4 px-8 rounded-2xl font-bold text-xl',
              'bg-gradient-to-r from-teal-500 to-green-500 text-white',
              'hover:from-teal-400 hover:to-green-400',
              'focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 focus:ring-offset-gray-900',
              'transition-all duration-200 transform hover:scale-105 active:scale-95'
            )}
          >
            {t('startTimer')}
          </button>
        </div>
      )}

      {/* Active timer state */}
      {(state.isRunning || state.isPaused) && !state.isComplete && (
        <div className="w-full max-w-md space-y-6">
          {/* Phase indicator */}
          <div className="flex justify-center">
            <PhaseIndicator
              phase={state.phase}
              isPulsing={state.isRunning && !state.isPaused}
            />
          </div>

          {/* Circular timer */}
          <div className="flex justify-center py-4">
            <CircularProgress
              progress={intervalProgressPercent}
              size={280}
              strokeWidth={16}
              color={phaseColor}
            >
              <div className="text-center">
                <div className="text-6xl font-bold text-white tabular-nums">
                  {formattedTimeRemaining}
                </div>
                <div className="mt-2 text-sm text-gray-500">
                  {t('remaining')}
                </div>
              </div>
            </CircularProgress>
          </div>

          {/* Interval progress */}
          <div className="text-center space-y-2">
            <div className="text-lg font-semibold text-white">
              {t('intervalProgress', {
                current: state.currentInterval + 1,
                total: intervals.repetitions,
              })}
            </div>

            {/* Interval dots */}
            <div className="flex justify-center gap-1.5 flex-wrap max-w-xs mx-auto">
              {Array.from({ length: intervals.repetitions }).map((_, i) => (
                <div
                  key={i}
                  className={cn(
                    'w-3 h-3 rounded-full transition-all duration-300',
                    i < state.currentInterval
                      ? 'bg-teal-500'
                      : i === state.currentInterval
                        ? state.phase === 'run'
                          ? 'bg-green-500 ring-2 ring-green-500/50 ring-offset-2 ring-offset-gray-900'
                          : 'bg-blue-500 ring-2 ring-blue-500/50 ring-offset-2 ring-offset-gray-900'
                        : 'bg-gray-700'
                  )}
                />
              ))}
            </div>
          </div>

          {/* Overall progress bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">{formattedTotalElapsed}</span>
              <span className="text-gray-400">
                {formatTimeDisplay(totalWorkoutDuration)}
              </span>
            </div>
            <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-teal-500 to-green-500 transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>

          {/* Controls */}
          <div className="grid grid-cols-3 gap-3">
            {state.isPaused ? (
              <ControlButton onClick={resume} variant="primary">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
                    clipRule="evenodd"
                  />
                </svg>
                {t('resume')}
              </ControlButton>
            ) : (
              <ControlButton onClick={pause} variant="secondary">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
                {t('pause')}
              </ControlButton>
            )}

            <ControlButton onClick={skipToNext} variant="secondary">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M10.293 15.707a1 1 0 010-1.414L14.586 10l-4.293-4.293a1 1 0 111.414-1.414l5 5a1 1 0 010 1.414l-5 5a1 1 0 01-1.414 0z"
                  clipRule="evenodd"
                />
                <path
                  fillRule="evenodd"
                  d="M4.293 15.707a1 1 0 010-1.414L8.586 10 4.293 5.707a1 1 0 011.414-1.414l5 5a1 1 0 010 1.414l-5 5a1 1 0 01-1.414 0z"
                  clipRule="evenodd"
                />
              </svg>
              {t('skip')}
            </ControlButton>

            <ControlButton onClick={handleStopClick} variant="danger">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z"
                  clipRule="evenodd"
                />
              </svg>
              {t('stop')}
            </ControlButton>
          </div>
        </div>
      )}

      {/* Completed state */}
      {state.isComplete && (
        <div className="text-center space-y-8">
          <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-green-500/20 border-2 border-green-500">
            <svg
              className="w-12 h-12 text-green-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>

          <div>
            <h2 className="text-3xl font-bold text-white">
              {t('workoutComplete')}
            </h2>
            <p className="mt-2 text-xl text-gray-400">
              {t('greatJob')}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4 max-w-xs mx-auto">
            <div className="p-4 bg-gray-800 rounded-xl">
              <div className="text-2xl font-bold text-teal-400">
                {formattedTotalElapsed}
              </div>
              <div className="text-sm text-gray-500">{t('duration')}</div>
            </div>
            <div className="p-4 bg-gray-800 rounded-xl">
              <div className="text-2xl font-bold text-purple-400">
                {intervals.repetitions}
              </div>
              <div className="text-sm text-gray-500">{t('intervalsCompleted')}</div>
            </div>
          </div>

          <button
            type="button"
            onClick={reset}
            className={cn(
              'py-3 px-8 rounded-xl font-semibold',
              'bg-gray-700 text-white',
              'hover:bg-gray-600',
              'focus:outline-none focus:ring-2 focus:ring-gray-500',
              'transition-all duration-200'
            )}
          >
            {t('startAgain')}
          </button>
        </div>
      )}

      {/* Stop confirmation dialog */}
      {showConfirmStop && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-sm p-6 bg-gray-800 rounded-2xl border border-gray-700 shadow-xl">
            <h3 className="text-lg font-semibold text-white">
              {t('stopConfirmTitle')}
            </h3>
            <p className="mt-2 text-sm text-gray-400">
              {t('stopConfirmMessage')}
            </p>

            <div className="mt-6 flex gap-3">
              <button
                type="button"
                onClick={() => setShowConfirmStop(false)}
                className={cn(
                  'flex-1 py-2.5 px-4 rounded-lg font-medium',
                  'border border-gray-600 text-gray-300',
                  'hover:bg-gray-700',
                  'focus:outline-none focus:ring-2 focus:ring-gray-500'
                )}
              >
                {t('continueWorkout')}
              </button>
              <button
                type="button"
                onClick={confirmStop}
                className={cn(
                  'flex-1 py-2.5 px-4 rounded-lg font-medium',
                  'bg-red-500 text-white',
                  'hover:bg-red-400',
                  'focus:outline-none focus:ring-2 focus:ring-red-500'
                )}
              >
                {t('stopWorkout')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default RunWalkTimer;
