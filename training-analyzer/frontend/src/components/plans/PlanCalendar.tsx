'use client';

import { useState, useMemo } from 'react';
import { clsx } from 'clsx';
import { format, parseISO, isThisWeek } from 'date-fns';
import { WeekView, PHASE_CONFIG } from './WeekView';
import type { TrainingPlan, TrainingSession, TrainingPhase } from '@/lib/types';

interface PlanCalendarProps {
  plan: TrainingPlan;
  onSessionComplete?: (sessionId: string) => void;
  onSessionSkip?: (sessionId: string) => void;
  onSessionClick?: (session: TrainingSession) => void;
}

export function PlanCalendar({
  plan,
  onSessionComplete,
  onSessionSkip,
  onSessionClick,
}: PlanCalendarProps) {
  const [expandedWeeks, setExpandedWeeks] = useState<Set<number>>(() => {
    // Auto-expand current week
    const currentWeekIndex = plan.weeks.findIndex((w) =>
      isThisWeek(parseISO(w.startDate), { weekStartsOn: 1 })
    );
    return new Set(currentWeekIndex >= 0 ? [currentWeekIndex] : []);
  });
  const [viewMode, setViewMode] = useState<'timeline' | 'list'>('timeline');

  const toggleWeek = (index: number) => {
    setExpandedWeeks((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const expandAll = () => {
    setExpandedWeeks(new Set(plan.weeks.map((_, i) => i)));
  };

  const collapseAll = () => {
    setExpandedWeeks(new Set());
  };

  // Group weeks by phase for timeline view
  const phaseGroups = useMemo(() => {
    const groups: { phase: TrainingPhase; weeks: typeof plan.weeks; startIndex: number }[] = [];
    let currentPhase: TrainingPhase | null = null;
    let currentGroup: typeof plan.weeks = [];
    let startIndex = 0;

    plan.weeks.forEach((week, index) => {
      if (week.phase !== currentPhase) {
        if (currentGroup.length > 0 && currentPhase) {
          groups.push({ phase: currentPhase, weeks: currentGroup, startIndex });
        }
        currentPhase = week.phase;
        currentGroup = [week];
        startIndex = index;
      } else {
        currentGroup.push(week);
      }
    });

    if (currentGroup.length > 0 && currentPhase) {
      groups.push({ phase: currentPhase, weeks: currentGroup, startIndex });
    }

    return groups;
  }, [plan.weeks]);

  // Calculate overall progress
  const progressPercentage = Math.round((plan.currentWeek / plan.totalWeeks) * 100);

  return (
    <div className="space-y-6">
      {/* Calendar Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-gray-100">{plan.name}</h2>
          <p className="text-sm text-gray-400">
            Week {plan.currentWeek} of {plan.totalWeeks} -{' '}
            {format(parseISO(plan.startDate), 'MMM d')} to{' '}
            {format(parseISO(plan.endDate), 'MMM d, yyyy')}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* View mode toggle */}
          <div className="flex bg-gray-800 rounded-lg p-1">
            <button
              onClick={() => setViewMode('timeline')}
              className={clsx(
                'px-3 py-1 text-sm font-medium rounded-md transition-colors',
                viewMode === 'timeline'
                  ? 'bg-gray-700 text-gray-100'
                  : 'text-gray-400 hover:text-gray-200'
              )}
            >
              Timeline
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={clsx(
                'px-3 py-1 text-sm font-medium rounded-md transition-colors',
                viewMode === 'list'
                  ? 'bg-gray-700 text-gray-100'
                  : 'text-gray-400 hover:text-gray-200'
              )}
            >
              List
            </button>
          </div>

          {/* Expand/Collapse buttons */}
          <button
            onClick={expandAll}
            className="px-3 py-1.5 text-sm text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded-lg transition-colors"
          >
            Expand All
          </button>
          <button
            onClick={collapseAll}
            className="px-3 py-1.5 text-sm text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded-lg transition-colors"
          >
            Collapse All
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-300">Plan Progress</span>
          <span className="text-sm text-gray-400">{progressPercentage}% complete</span>
        </div>
        <div className="h-3 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-teal-500 to-teal-400 rounded-full transition-all duration-500"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
      </div>

      {/* Phase Legend */}
      <div className="flex flex-wrap gap-3">
        {Object.entries(PHASE_CONFIG).map(([phase, config]) => (
          <div key={phase} className="flex items-center gap-2">
            <div
              className={clsx(
                'w-3 h-3 rounded-full border-2',
                config.borderColor,
                config.bgColor
              )}
            />
            <span className="text-xs text-gray-400">{config.label}</span>
          </div>
        ))}
      </div>

      {/* Timeline View */}
      {viewMode === 'timeline' && (
        <div className="space-y-8">
          {phaseGroups.map((group, groupIndex) => {
            const phaseConfig = PHASE_CONFIG[group.phase];
            return (
              <div key={groupIndex} className="relative">
                {/* Phase header */}
                <div
                  className={clsx(
                    'sticky top-0 z-10 px-4 py-2 rounded-lg mb-4',
                    phaseConfig.bgColor,
                    'border',
                    phaseConfig.borderColor
                  )}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className={clsx('font-bold', phaseConfig.color)}>
                        {phaseConfig.label} Phase
                      </h3>
                      <p className="text-sm text-gray-400">
                        {phaseConfig.description}
                      </p>
                    </div>
                    <span className="text-sm text-gray-500">
                      {group.weeks.length} week{group.weeks.length !== 1 && 's'}
                    </span>
                  </div>
                </div>

                {/* Weeks in this phase */}
                <div className="space-y-4 pl-4 border-l-4 border-gray-700 ml-2">
                  {group.weeks.map((week, weekIndex) => {
                    const globalIndex = group.startIndex + weekIndex;
                    return (
                      <div key={week.id} className="relative">
                        {/* Timeline dot */}
                        <div
                          className={clsx(
                            'absolute -left-[1.25rem] top-4 w-4 h-4 rounded-full border-2 bg-gray-900',
                            phaseConfig.borderColor
                          )}
                        />
                        <WeekView
                          week={week}
                          expanded={expandedWeeks.has(globalIndex)}
                          onToggleExpand={() => toggleWeek(globalIndex)}
                          onSessionComplete={onSessionComplete}
                          onSessionSkip={onSessionSkip}
                          onSessionClick={onSessionClick}
                        />
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* List View */}
      {viewMode === 'list' && (
        <div className="space-y-4">
          {plan.weeks.map((week, index) => (
            <WeekView
              key={week.id}
              week={week}
              expanded={expandedWeeks.has(index)}
              onToggleExpand={() => toggleWeek(index)}
              onSessionComplete={onSessionComplete}
              onSessionSkip={onSessionSkip}
              onSessionClick={onSessionClick}
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {plan.weeks.length === 0 && (
        <div className="text-center py-12 bg-gray-900 rounded-xl border border-gray-800">
          <svg
            className="w-12 h-12 text-gray-600 mx-auto mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <h3 className="text-lg font-medium text-gray-100 mb-1">
            No weeks scheduled
          </h3>
          <p className="text-sm text-gray-500">
            This plan doesn&apos;t have any training weeks yet.
          </p>
        </div>
      )}
    </div>
  );
}
