'use client';

import { clsx } from 'clsx';
import { format, parseISO, isToday, isPast, isFuture } from 'date-fns';
import type { TrainingSession, SessionType, CompletionStatus } from '@/lib/types';

// Session type configuration - dark theme
const SESSION_TYPE_CONFIG: Record<
  SessionType,
  { label: string; color: string; bgColor: string; icon: string }
> = {
  easy: {
    label: 'Easy Run',
    color: 'text-green-400',
    bgColor: 'bg-green-900/50',
    icon: '🏃',
  },
  long_run: {
    label: 'Long Run',
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/50',
    icon: '🏃‍♂️',
  },
  tempo: {
    label: 'Tempo',
    color: 'text-orange-400',
    bgColor: 'bg-orange-900/50',
    icon: '⚡',
  },
  interval: {
    label: 'Intervals',
    color: 'text-red-400',
    bgColor: 'bg-red-900/50',
    icon: '🔥',
  },
  hill: {
    label: 'Hill Repeats',
    color: 'text-amber-400',
    bgColor: 'bg-amber-900/50',
    icon: '⛰️',
  },
  recovery: {
    label: 'Recovery',
    color: 'text-teal-400',
    bgColor: 'bg-teal-900/50',
    icon: '🧘',
  },
  race: {
    label: 'Race',
    color: 'text-purple-400',
    bgColor: 'bg-purple-900/50',
    icon: '🏆',
  },
  cross_training: {
    label: 'Cross Training',
    color: 'text-indigo-400',
    bgColor: 'bg-indigo-900/50',
    icon: '🚴',
  },
  strength: {
    label: 'Strength',
    color: 'text-slate-400',
    bgColor: 'bg-slate-800',
    icon: '💪',
  },
  rest: {
    label: 'Rest Day',
    color: 'text-gray-500',
    bgColor: 'bg-gray-800',
    icon: '😴',
  },
};

// Completion status configuration - dark theme
const STATUS_CONFIG: Record<
  CompletionStatus,
  { label: string; color: string; bgColor: string; borderColor: string }
> = {
  pending: {
    label: 'Scheduled',
    color: 'text-gray-400',
    bgColor: 'bg-gray-900',
    borderColor: 'border-gray-700',
  },
  completed: {
    label: 'Completed',
    color: 'text-green-400',
    bgColor: 'bg-green-900/30',
    borderColor: 'border-green-700',
  },
  skipped: {
    label: 'Skipped',
    color: 'text-amber-400',
    bgColor: 'bg-amber-900/30',
    borderColor: 'border-amber-700',
  },
  partial: {
    label: 'Partial',
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/30',
    borderColor: 'border-blue-700',
  },
};

interface SessionCardProps {
  session: TrainingSession;
  onComplete?: (sessionId: string) => void;
  onSkip?: (sessionId: string) => void;
  onClick?: (session: TrainingSession) => void;
  compact?: boolean;
  showDate?: boolean;
}

export function SessionCard({
  session,
  onComplete,
  onSkip,
  onClick,
  compact = false,
  showDate = true,
}: SessionCardProps) {
  const typeConfig = SESSION_TYPE_CONFIG[session.sessionType];
  const statusConfig = STATUS_CONFIG[session.completionStatus];
  const sessionDate = parseISO(session.date);
  const isSessionToday = isToday(sessionDate);
  const isSessionPast = isPast(sessionDate) && !isSessionToday;
  const isSessionFuture = isFuture(sessionDate);

  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${minutes}min`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}min` : `${hours}h`;
  };

  const formatDistance = (meters: number) => {
    if (meters >= 1000) {
      return `${(meters / 1000).toFixed(1)}km`;
    }
    return `${meters}m`;
  };

  const formatPace = (secondsPerKm: number) => {
    const minutes = Math.floor(secondsPerKm / 60);
    const seconds = Math.round(secondsPerKm % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}/km`;
  };

  if (compact) {
    return (
      <button
        onClick={() => onClick?.(session)}
        className={clsx(
          'w-full text-left p-2 rounded-lg border transition-all',
          'hover:border-gray-600 hover:bg-gray-800/50',
          statusConfig.bgColor,
          statusConfig.borderColor,
          isSessionToday && 'ring-2 ring-teal-500'
        )}
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">{typeConfig.icon}</span>
          <div className="flex-1 min-w-0">
            <p className={clsx('font-medium text-sm truncate', typeConfig.color)}>
              {session.name}
            </p>
            <p className="text-xs text-gray-500">
              {formatDuration(session.targetDuration)}
            </p>
          </div>
          {session.completionStatus === 'completed' && (
            <svg
              className="w-4 h-4 text-green-500"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                clipRule="evenodd"
              />
            </svg>
          )}
        </div>
      </button>
    );
  }

  return (
    <div
      className={clsx(
        'rounded-xl border-2 overflow-hidden transition-all',
        statusConfig.bgColor,
        statusConfig.borderColor,
        isSessionToday && 'ring-2 ring-teal-500 ring-offset-2 ring-offset-gray-900',
        onClick && 'cursor-pointer hover:border-gray-600'
      )}
      onClick={() => onClick?.(session)}
    >
      {/* Header */}
      <div className={clsx('px-4 py-3', typeConfig.bgColor)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">{typeConfig.icon}</span>
            <div>
              <h3 className={clsx('font-semibold', typeConfig.color)}>
                {session.name}
              </h3>
              <span
                className={clsx(
                  'text-xs px-2 py-0.5 rounded-full',
                  typeConfig.bgColor,
                  typeConfig.color,
                  'border border-current'
                )}
              >
                {typeConfig.label}
              </span>
            </div>
          </div>
          {showDate && (
            <div className="text-right">
              <p
                className={clsx(
                  'text-sm font-medium',
                  isSessionToday ? 'text-teal-400' : 'text-gray-400'
                )}
              >
                {isSessionToday ? 'Today' : format(sessionDate, 'EEE, MMM d')}
              </p>
              <span
                className={clsx(
                  'text-xs px-2 py-0.5 rounded-full inline-block',
                  statusConfig.color,
                  'bg-gray-800'
                )}
              >
                {statusConfig.label}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="px-4 py-3 space-y-3">
        {/* Description */}
        {session.description && (
          <p className="text-sm text-gray-300">{session.description}</p>
        )}

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-gray-800 rounded-lg p-2 text-center">
            <p className="text-xs text-gray-500 uppercase">Duration</p>
            <p className="font-semibold text-gray-100">
              {formatDuration(session.targetDuration)}
            </p>
            {session.actualDuration && (
              <p className="text-xs text-green-400">
                Actual: {formatDuration(session.actualDuration)}
              </p>
            )}
          </div>

          {session.targetDistance && (
            <div className="bg-gray-800 rounded-lg p-2 text-center">
              <p className="text-xs text-gray-500 uppercase">Distance</p>
              <p className="font-semibold text-gray-100">
                {formatDistance(session.targetDistance)}
              </p>
              {session.actualDistance && (
                <p className="text-xs text-green-400">
                  Actual: {formatDistance(session.actualDistance)}
                </p>
              )}
            </div>
          )}

          {session.targetPace && (
            <div className="bg-gray-800 rounded-lg p-2 text-center">
              <p className="text-xs text-gray-500 uppercase">Target Pace</p>
              <p className="font-semibold text-gray-100">
                {formatPace(session.targetPace)}
              </p>
              {session.actualPace && (
                <p className="text-xs text-green-400">
                  Actual: {formatPace(session.actualPace)}
                </p>
              )}
            </div>
          )}

          <div className="bg-gray-800 rounded-lg p-2 text-center">
            <p className="text-xs text-gray-500 uppercase">Load</p>
            <p className="font-semibold text-gray-100">{session.targetLoad}</p>
            {session.actualLoad && (
              <p className="text-xs text-green-400">
                Actual: {session.actualLoad}
              </p>
            )}
          </div>
        </div>

        {/* Workout Structure */}
        {(session.warmup || session.mainSet || session.cooldown) && (
          <div className="border-t border-gray-700 pt-3 space-y-2">
            {session.warmup && (
              <div className="flex gap-2">
                <span className="text-xs font-medium text-blue-400 w-20">
                  Warm-up
                </span>
                <span className="text-xs text-gray-300">{session.warmup}</span>
              </div>
            )}
            {session.mainSet && (
              <div className="flex gap-2">
                <span className="text-xs font-medium text-red-400 w-20">
                  Main Set
                </span>
                <span className="text-xs text-gray-300">{session.mainSet}</span>
              </div>
            )}
            {session.cooldown && (
              <div className="flex gap-2">
                <span className="text-xs font-medium text-purple-400 w-20">
                  Cool-down
                </span>
                <span className="text-xs text-gray-300">{session.cooldown}</span>
              </div>
            )}
          </div>
        )}

        {/* Notes */}
        {session.notes && (
          <div className="border-t border-gray-700 pt-3">
            <p className="text-xs text-gray-500 mb-1">Notes</p>
            <p className="text-sm text-gray-300 italic">{session.notes}</p>
          </div>
        )}

        {/* Actions */}
        {session.completionStatus === 'pending' &&
          (isSessionToday || isSessionPast) &&
          (onComplete || onSkip) && (
            <div className="border-t border-gray-700 pt-3 flex gap-2">
              {onComplete && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onComplete(session.id);
                  }}
                  className="flex-1 px-4 py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-500 transition-colors"
                >
                  Mark Complete
                </button>
              )}
              {onSkip && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onSkip(session.id);
                  }}
                  className="px-4 py-2 bg-gray-700 text-gray-300 text-sm font-medium rounded-lg hover:bg-gray-600 transition-colors"
                >
                  Skip
                </button>
              )}
            </div>
          )}
      </div>
    </div>
  );
}

// Export session type config for use in other components
export { SESSION_TYPE_CONFIG, STATUS_CONFIG };
