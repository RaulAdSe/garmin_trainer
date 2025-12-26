'use client';

import { clsx } from 'clsx';
import { format, parseISO, isThisWeek, addDays } from 'date-fns';
import { SessionCard, SESSION_TYPE_CONFIG } from './SessionCard';
import type { TrainingWeek, TrainingPhase, TrainingSession } from '@/lib/types';

// Phase configuration - dark theme
const PHASE_CONFIG: Record<
  TrainingPhase,
  { label: string; color: string; bgColor: string; borderColor: string; description: string }
> = {
  base: {
    label: 'Base',
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/30',
    borderColor: 'border-blue-700',
    description: 'Building aerobic foundation and volume',
  },
  build: {
    label: 'Build',
    color: 'text-orange-400',
    bgColor: 'bg-orange-900/30',
    borderColor: 'border-orange-700',
    description: 'Increasing intensity and race-specific work',
  },
  peak: {
    label: 'Peak',
    color: 'text-red-400',
    bgColor: 'bg-red-900/30',
    borderColor: 'border-red-700',
    description: 'Maximum fitness and race simulation',
  },
  taper: {
    label: 'Taper',
    color: 'text-green-400',
    bgColor: 'bg-green-900/30',
    borderColor: 'border-green-700',
    description: 'Reducing volume while maintaining intensity',
  },
  recovery: {
    label: 'Recovery',
    color: 'text-purple-400',
    bgColor: 'bg-purple-900/30',
    borderColor: 'border-purple-700',
    description: 'Active recovery and regeneration',
  },
};

const DAYS_OF_WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

interface WeekViewProps {
  week: TrainingWeek;
  onSessionComplete?: (sessionId: string) => void;
  onSessionSkip?: (sessionId: string) => void;
  onSessionClick?: (session: TrainingSession) => void;
  expanded?: boolean;
  onToggleExpand?: () => void;
  isCurrentWeek?: boolean;
}

export function WeekView({
  week,
  onSessionComplete,
  onSessionSkip,
  onSessionClick,
  expanded = false,
  onToggleExpand,
  isCurrentWeek: isCurrentWeekProp,
}: WeekViewProps) {
  const phaseConfig = PHASE_CONFIG[week.phase];
  const weekStart = parseISO(week.startDate);
  const isCurrentWeek = isCurrentWeekProp ?? isThisWeek(weekStart, { weekStartsOn: 1 });

  // Organize sessions by day of week
  const sessionsByDay = week.sessions.reduce(
    (acc, session) => {
      acc[session.dayOfWeek] = [...(acc[session.dayOfWeek] || []), session];
      return acc;
    },
    {} as Record<number, TrainingSession[]>
  );

  // Calculate load adherence
  const loadAdherence =
    week.targetLoad > 0
      ? Math.round((week.actualLoad / week.targetLoad) * 100)
      : 0;

  // Count completed sessions
  const completedSessions = week.sessions.filter(
    (s) => s.completionStatus === 'completed'
  ).length;
  const totalSessions = week.sessions.filter(
    (s) => s.sessionType !== 'rest'
  ).length;

  return (
    <div
      className={clsx(
        'rounded-xl border-2 overflow-hidden transition-all',
        phaseConfig.borderColor,
        isCurrentWeek && 'ring-2 ring-teal-500 ring-offset-2 ring-offset-gray-950'
      )}
    >
      {/* Week Header */}
      <div
        className={clsx(
          'px-4 py-3 cursor-pointer transition-colors',
          phaseConfig.bgColor,
          'hover:brightness-110'
        )}
        onClick={onToggleExpand}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-gray-100">Week {week.weekNumber}</h3>
                {isCurrentWeek && (
                  <span className="text-xs px-2 py-0.5 bg-teal-600 text-white rounded-full">
                    Current
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-400">
                {format(weekStart, 'MMM d')} -{' '}
                {format(parseISO(week.endDate), 'MMM d')}
              </p>
            </div>
            <span
              className={clsx(
                'px-3 py-1 rounded-full text-sm font-medium',
                phaseConfig.bgColor,
                phaseConfig.color,
                'border',
                phaseConfig.borderColor
              )}
            >
              {phaseConfig.label}
            </span>
          </div>

          <div className="flex items-center gap-4">
            {/* Load indicator */}
            <div className="text-right hidden sm:block">
              <p className="text-xs text-gray-500">Load</p>
              <div className="flex items-center gap-1">
                <span className="font-semibold text-gray-100">
                  {week.actualLoad}
                </span>
                <span className="text-gray-600">/</span>
                <span className="text-gray-400">{week.targetLoad}</span>
              </div>
            </div>

            {/* Progress indicator */}
            <div className="text-right hidden sm:block">
              <p className="text-xs text-gray-500">Sessions</p>
              <span className="font-semibold text-gray-100">
                {completedSessions}/{totalSessions}
              </span>
            </div>

            {/* Load adherence bar */}
            <div className="w-24 hidden md:block">
              <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={clsx(
                    'h-full rounded-full transition-all',
                    loadAdherence >= 90
                      ? 'bg-teal-500'
                      : loadAdherence >= 70
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                  )}
                  style={{ width: `${Math.min(loadAdherence, 100)}%` }}
                />
              </div>
              <p className="text-xs text-gray-500 text-center mt-0.5">
                {loadAdherence}%
              </p>
            </div>

            {/* Expand/collapse icon */}
            <button className="p-1 hover:bg-gray-800 rounded transition-colors">
              <svg
                className={clsx(
                  'w-5 h-5 text-gray-400 transition-transform',
                  expanded && 'rotate-180'
                )}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Phase description */}
        <p className="text-xs text-gray-500 mt-1">{phaseConfig.description}</p>

        {/* Focus areas */}
        {week.focusAreas.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {week.focusAreas.map((focus, i) => (
              <span
                key={i}
                className="text-xs px-2 py-0.5 bg-gray-800 rounded-full text-gray-400"
              >
                {focus}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-gray-800">
          {/* Day grid - desktop */}
          <div className="hidden md:grid grid-cols-7 divide-x divide-gray-800">
            {DAYS_OF_WEEK.map((day, index) => {
              const dayDate = addDays(weekStart, index);
              const daySessions = sessionsByDay[index] || [];

              return (
                <div key={day} className="min-h-[120px]">
                  {/* Day header */}
                  <div className="px-2 py-1 bg-gray-900 border-b border-gray-800 text-center">
                    <p className="text-xs font-medium text-gray-500">{day}</p>
                    <p className="text-sm font-semibold text-gray-100">
                      {format(dayDate, 'd')}
                    </p>
                  </div>

                  {/* Sessions */}
                  <div className="p-1 space-y-1 bg-gray-950">
                    {daySessions.length === 0 ? (
                      <div className="text-xs text-gray-600 text-center py-4">
                        Rest
                      </div>
                    ) : (
                      daySessions.map((session) => (
                        <SessionCard
                          key={session.id}
                          session={session}
                          compact
                          showDate={false}
                          onClick={onSessionClick}
                        />
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Session list for mobile */}
          <div className="md:hidden p-4 space-y-3 bg-gray-950">
            <h4 className="font-medium text-gray-300">Sessions this week</h4>
            {week.sessions
              .filter((s) => s.sessionType !== 'rest')
              .sort((a, b) => a.dayOfWeek - b.dayOfWeek)
              .map((session) => (
                <SessionCard
                  key={session.id}
                  session={session}
                  onComplete={onSessionComplete}
                  onSkip={onSessionSkip}
                  onClick={onSessionClick}
                />
              ))}
          </div>

          {/* Week notes */}
          {week.notes && (
            <div className="px-4 py-3 bg-gray-900 border-t border-gray-800">
              <p className="text-xs text-gray-500 mb-1">Week Notes</p>
              <p className="text-sm text-gray-300">{week.notes}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Export phase config for use in other components
export { PHASE_CONFIG };
