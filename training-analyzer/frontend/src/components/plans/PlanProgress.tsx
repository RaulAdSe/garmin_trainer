'use client';

import { useMemo } from 'react';
import { clsx } from 'clsx';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  LineChart,
  Line,
  ReferenceLine,
} from 'recharts';
import { PHASE_CONFIG } from './WeekView';
import type { TrainingPlan, PlanCompliance, TrainingPhase } from '@/lib/types';

interface PlanProgressProps {
  plan: TrainingPlan;
  compliance?: PlanCompliance;
}

export function PlanProgress({ plan, compliance: complianceProp }: PlanProgressProps) {
  // Use provided compliance or plan's compliance
  const compliance = complianceProp || plan.compliance;

  // Calculate derived metrics
  const metrics = useMemo(() => {
    const { totalSessions, completedSessions, skippedSessions, partialSessions } = compliance;
    const pendingSessions = totalSessions - completedSessions - skippedSessions - partialSessions;

    return {
      totalSessions,
      completedSessions,
      skippedSessions,
      partialSessions,
      pendingSessions,
      completionRate: totalSessions > 0 ? (completedSessions / totalSessions) * 100 : 0,
      effectiveCompletionRate:
        totalSessions > 0
          ? ((completedSessions + partialSessions * 0.5) / totalSessions) * 100
          : 0,
    };
  }, [compliance]);

  // Prepare chart data
  const weeklyChartData = useMemo(() => {
    return compliance.weeklyCompliance.map((week) => ({
      week: `W${week.weekNumber}`,
      weekNumber: week.weekNumber,
      targetLoad: week.targetLoad,
      actualLoad: week.actualLoad,
      adherence: week.adherence,
      sessionsPlanned: week.sessionsPlanned,
      sessionsCompleted: week.sessionsCompleted,
      phase: plan.weeks[week.weekNumber - 1]?.phase || 'base',
    }));
  }, [compliance.weeklyCompliance, plan.weeks]);

  // Current phase
  const currentPhase = plan.weeks[plan.currentWeek - 1]?.phase || 'base';
  const currentPhaseConfig = PHASE_CONFIG[currentPhase];

  // Phase breakdown
  const phaseBreakdown = useMemo(() => {
    const breakdown: Record<TrainingPhase, { weeks: number; completed: number }> = {
      base: { weeks: 0, completed: 0 },
      build: { weeks: 0, completed: 0 },
      peak: { weeks: 0, completed: 0 },
      taper: { weeks: 0, completed: 0 },
      recovery: { weeks: 0, completed: 0 },
    };

    plan.weeks.forEach((week, index) => {
      breakdown[week.phase].weeks++;
      if (index < plan.currentWeek) {
        breakdown[week.phase].completed++;
      }
    });

    return breakdown;
  }, [plan.weeks, plan.currentWeek]);

  // Chart colors for dark theme
  const chartColors = {
    grid: '#374151',
    text: '#9ca3af',
    target: '#4b5563',
    actual: '#14b8a6',
    adherenceLine: '#14b8a6',
    referenceGreen: '#22c55e',
    referenceYellow: '#eab308',
  };

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Compliance Card */}
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-500">Compliance</p>
            <svg
              className="w-5 h-5 text-teal-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <p className="text-2xl font-bold text-gray-100">
            {compliance.compliancePercentage}%
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {metrics.completedSessions} of {metrics.totalSessions} sessions
          </p>
        </div>

        {/* Load Adherence Card */}
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-500">Load Adherence</p>
            <svg
              className="w-5 h-5 text-blue-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
              />
            </svg>
          </div>
          <p className="text-2xl font-bold text-gray-100">
            {compliance.loadAdherence}%
          </p>
          <p className="text-xs text-gray-500 mt-1">of target training load</p>
        </div>

        {/* Current Week Card */}
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-500">Current Week</p>
            <svg
              className="w-5 h-5 text-purple-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </div>
          <p className="text-2xl font-bold text-gray-100">
            {plan.currentWeek}/{plan.totalWeeks}
          </p>
          <p
            className={clsx(
              'text-xs mt-1 px-2 py-0.5 rounded-full inline-block',
              currentPhaseConfig.color,
              currentPhaseConfig.bgColor
            )}
          >
            {currentPhaseConfig.label} Phase
          </p>
        </div>

        {/* Progress Card */}
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-500">Progress</p>
            <svg
              className="w-5 h-5 text-orange-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <p className="text-2xl font-bold text-gray-100">
            {Math.round((plan.currentWeek / plan.totalWeeks) * 100)}%
          </p>
          <p className="text-xs text-gray-500 mt-1">of plan completed</p>
        </div>
      </div>

      {/* Session Breakdown */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">
          Session Breakdown
        </h3>

        <div className="grid grid-cols-4 gap-4 mb-4">
          <div className="text-center">
            <p className="text-3xl font-bold text-teal-400">
              {metrics.completedSessions}
            </p>
            <p className="text-sm text-gray-500">Completed</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-blue-400">
              {metrics.partialSessions}
            </p>
            <p className="text-sm text-gray-500">Partial</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-amber-400">
              {metrics.skippedSessions}
            </p>
            <p className="text-sm text-gray-500">Skipped</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-gray-500">
              {metrics.pendingSessions}
            </p>
            <p className="text-sm text-gray-500">Remaining</p>
          </div>
        </div>

        {/* Session distribution bar */}
        <div className="h-4 bg-gray-800 rounded-full overflow-hidden flex">
          <div
            className="bg-teal-500 transition-all"
            style={{
              width: `${(metrics.completedSessions / metrics.totalSessions) * 100}%`,
            }}
          />
          <div
            className="bg-blue-500 transition-all"
            style={{
              width: `${(metrics.partialSessions / metrics.totalSessions) * 100}%`,
            }}
          />
          <div
            className="bg-amber-500 transition-all"
            style={{
              width: `${(metrics.skippedSessions / metrics.totalSessions) * 100}%`,
            }}
          />
        </div>

        <div className="flex justify-center gap-6 mt-3">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-teal-500 rounded-full" />
            <span className="text-xs text-gray-400">Completed</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-blue-500 rounded-full" />
            <span className="text-xs text-gray-400">Partial</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-amber-500 rounded-full" />
            <span className="text-xs text-gray-400">Skipped</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-gray-700 rounded-full" />
            <span className="text-xs text-gray-400">Remaining</span>
          </div>
        </div>
      </div>

      {/* Weekly Load Chart */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">
          Weekly Training Load
        </h3>

        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={weeklyChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
              <XAxis
                dataKey="week"
                stroke={chartColors.text}
                fontSize={12}
                tickLine={false}
              />
              <YAxis stroke={chartColors.text} fontSize={12} tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1f2937',
                  border: '1px solid #374151',
                  borderRadius: '0.5rem',
                  color: '#f3f4f6',
                }}
                labelStyle={{ color: '#f3f4f6' }}
                formatter={(value: number, name: string) => [
                  value,
                  name === 'targetLoad' ? 'Target' : 'Actual',
                ]}
              />
              <Legend wrapperStyle={{ color: chartColors.text }} />
              <Bar
                dataKey="targetLoad"
                fill={chartColors.target}
                name="Target"
                radius={[4, 4, 0, 0]}
              />
              <Bar
                dataKey="actualLoad"
                fill={chartColors.actual}
                name="Actual"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Weekly Adherence Chart */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">
          Load Adherence Trend
        </h3>

        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={weeklyChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
              <XAxis
                dataKey="week"
                stroke={chartColors.text}
                fontSize={12}
                tickLine={false}
              />
              <YAxis
                stroke={chartColors.text}
                fontSize={12}
                tickLine={false}
                domain={[0, 120]}
                tickFormatter={(value) => `${value}%`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1f2937',
                  border: '1px solid #374151',
                  borderRadius: '0.5rem',
                  color: '#f3f4f6',
                }}
                formatter={(value: number) => [`${value}%`, 'Adherence']}
              />
              <ReferenceLine
                y={100}
                stroke={chartColors.referenceGreen}
                strokeDasharray="5 5"
                label={{ value: '100%', fill: chartColors.referenceGreen, fontSize: 10 }}
              />
              <ReferenceLine
                y={80}
                stroke={chartColors.referenceYellow}
                strokeDasharray="5 5"
                label={{ value: '80%', fill: chartColors.referenceYellow, fontSize: 10 }}
              />
              <Line
                type="monotone"
                dataKey="adherence"
                stroke={chartColors.adherenceLine}
                strokeWidth={2}
                dot={{ fill: chartColors.adherenceLine, strokeWidth: 2, r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Phase Progress */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">
          Phase Progress
        </h3>

        <div className="space-y-4">
          {(Object.entries(phaseBreakdown) as [TrainingPhase, { weeks: number; completed: number }][])
            .filter(([_, data]) => data.weeks > 0)
            .map(([phase, data]) => {
              const config = PHASE_CONFIG[phase];
              const progress = data.weeks > 0 ? (data.completed / data.weeks) * 100 : 0;
              const isCurrentPhase = phase === currentPhase;

              return (
                <div key={phase}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={clsx(
                          'px-2 py-0.5 rounded-full text-xs font-medium',
                          config.bgColor,
                          config.color
                        )}
                      >
                        {config.label}
                      </span>
                      {isCurrentPhase && (
                        <span className="text-xs text-teal-400 font-medium">
                          Current
                        </span>
                      )}
                    </div>
                    <span className="text-sm text-gray-400">
                      {data.completed}/{data.weeks} weeks
                    </span>
                  </div>
                  <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className={clsx(
                        'h-full rounded-full transition-all',
                        phase === 'base'
                          ? 'bg-blue-500'
                          : phase === 'build'
                            ? 'bg-orange-500'
                            : phase === 'peak'
                              ? 'bg-red-500'
                              : phase === 'taper'
                                ? 'bg-green-500'
                                : 'bg-purple-500'
                      )}
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>
              );
            })}
        </div>
      </div>

      {/* Insights */}
      <div className="bg-gradient-to-r from-teal-900/30 to-blue-900/30 rounded-xl border border-teal-800 p-6">
        <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center gap-2">
          <svg
            className="w-5 h-5 text-teal-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          Training Insights
        </h3>

        <div className="space-y-3">
          {compliance.compliancePercentage >= 90 && (
            <div className="flex items-start gap-3 bg-gray-900/50 rounded-lg p-3">
              <span className="text-teal-400 text-lg">+</span>
              <p className="text-sm text-gray-300">
                Excellent consistency! You&apos;re hitting over 90% of your planned sessions.
              </p>
            </div>
          )}

          {compliance.compliancePercentage < 70 && compliance.compliancePercentage > 0 && (
            <div className="flex items-start gap-3 bg-gray-900/50 rounded-lg p-3">
              <span className="text-amber-400 text-lg">!</span>
              <p className="text-sm text-gray-300">
                Your compliance is below 70%. Consider adjusting your plan to better fit your schedule.
              </p>
            </div>
          )}

          {compliance.loadAdherence > 110 && (
            <div className="flex items-start gap-3 bg-gray-900/50 rounded-lg p-3">
              <span className="text-blue-400 text-lg">i</span>
              <p className="text-sm text-gray-300">
                You&apos;re exceeding planned load by {compliance.loadAdherence - 100}%. Watch for signs of overtraining.
              </p>
            </div>
          )}

          {compliance.loadAdherence < 80 && compliance.loadAdherence > 0 && (
            <div className="flex items-start gap-3 bg-gray-900/50 rounded-lg p-3">
              <span className="text-amber-400 text-lg">i</span>
              <p className="text-sm text-gray-300">
                Training load is {100 - compliance.loadAdherence}% below target. You may want to gradually increase intensity.
              </p>
            </div>
          )}

          {metrics.skippedSessions > metrics.completedSessions * 0.2 && (
            <div className="flex items-start gap-3 bg-gray-900/50 rounded-lg p-3">
              <span className="text-amber-400 text-lg">?</span>
              <p className="text-sm text-gray-300">
                You&apos;ve skipped {Math.round((metrics.skippedSessions / metrics.totalSessions) * 100)}% of sessions. Consider adapting your plan.
              </p>
            </div>
          )}

          {compliance.compliancePercentage > 0 &&
            compliance.compliancePercentage <= 100 &&
            compliance.loadAdherence >= 80 &&
            compliance.loadAdherence <= 110 &&
            metrics.skippedSessions <= metrics.completedSessions * 0.1 && (
              <div className="flex items-start gap-3 bg-gray-900/50 rounded-lg p-3">
                <span className="text-teal-400 text-lg">+</span>
                <p className="text-sm text-gray-300">
                  Great balance! Your training is well-aligned with your plan.
                </p>
              </div>
            )}
        </div>
      </div>
    </div>
  );
}
