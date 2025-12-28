'use client';

import { useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { Link, useRouter } from '@/i18n/navigation';
import { clsx } from 'clsx';
import { format, parseISO, differenceInWeeks } from 'date-fns';
import { PlanCalendar } from '@/components/plans/PlanCalendar';
import { PlanProgress } from '@/components/plans/PlanProgress';
import { SessionCard } from '@/components/plans/SessionCard';
import {
  usePlan,
  useActivatePlan,
  usePausePlan,
  useDeletePlan,
  useAdaptPlan,
  useCompleteSession,
  useSkipSession,
} from '@/hooks/usePlans';
import type { TrainingSession, TrainingPlan } from '@/lib/types';

const STATUS_CONFIG: Record<
  TrainingPlan['status'],
  { label: string; color: string; bgColor: string; borderColor: string }
> = {
  draft: {
    label: 'Draft',
    color: 'text-gray-400',
    bgColor: 'bg-gray-800',
    borderColor: 'border-gray-700',
  },
  active: {
    label: 'Active',
    color: 'text-green-400',
    bgColor: 'bg-green-900/50',
    borderColor: 'border-green-700',
  },
  completed: {
    label: 'Completed',
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/50',
    borderColor: 'border-blue-700',
  },
  paused: {
    label: 'Paused',
    color: 'text-amber-400',
    bgColor: 'bg-amber-900/50',
    borderColor: 'border-amber-700',
  },
  cancelled: {
    label: 'Cancelled',
    color: 'text-red-400',
    bgColor: 'bg-red-900/50',
    borderColor: 'border-red-700',
  },
};

const RACE_DISTANCE_LABELS: Record<string, string> = {
  '5k': '5K',
  '10k': '10K',
  half_marathon: 'Half Marathon',
  marathon: 'Marathon',
  ultra: 'Ultra Marathon',
  custom: 'Custom',
};

type ViewTab = 'calendar' | 'progress' | 'settings';

export default function PlanDetailPage() {
  const params = useParams();
  const router = useRouter();
  const planId = params.id as string;

  const [activeTab, setActiveTab] = useState<ViewTab>('calendar');
  const [selectedSession, setSelectedSession] = useState<TrainingSession | null>(null);
  const [showAdaptModal, setShowAdaptModal] = useState(false);
  const [adaptReason, setAdaptReason] = useState('');

  // Data fetching
  const { data: plan, isLoading, error } = usePlan(planId);

  // Mutations
  const activateMutation = useActivatePlan();
  const pauseMutation = usePausePlan();
  const deleteMutation = useDeletePlan();
  const adaptMutation = useAdaptPlan();
  const completeMutation = useCompleteSession();
  const skipMutation = useSkipSession();

  // Handlers
  const handleActivate = async () => {
    await activateMutation.mutateAsync(planId);
  };

  const handlePause = async () => {
    await pauseMutation.mutateAsync(planId);
  };

  const handleDelete = async () => {
    if (confirm('Are you sure you want to delete this plan? This action cannot be undone.')) {
      await deleteMutation.mutateAsync(planId);
      router.push('/plans');
    }
  };

  const handleAdapt = async () => {
    await adaptMutation.mutateAsync({ planId, reason: adaptReason || undefined });
    setShowAdaptModal(false);
    setAdaptReason('');
  };

  const handleCompleteSession = useCallback(
    async (sessionId: string) => {
      await completeMutation.mutateAsync({ planId, sessionId });
      setSelectedSession(null);
    },
    [completeMutation, planId]
  );

  const handleSkipSession = useCallback(
    async (sessionId: string) => {
      const notes = prompt('Why are you skipping this session? (optional)');
      await skipMutation.mutateAsync({
        planId,
        sessionId,
        notes: notes || undefined,
      });
      setSelectedSession(null);
    },
    [skipMutation, planId]
  );

  const handleSessionClick = useCallback((session: TrainingSession) => {
    setSelectedSession(session);
  }, []);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-teal-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading plan...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !plan) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="w-16 h-16 bg-red-900/50 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-red-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-100 mb-2">Plan not found</h2>
          <p className="text-gray-400 mb-4">
            {error instanceof Error ? error.message : 'The plan you are looking for does not exist.'}
          </p>
          <Link
            href="/plans"
            className="text-teal-400 hover:text-teal-300 font-medium"
          >
            Back to Plans
          </Link>
        </div>
      </div>
    );
  }

  const statusConfig = STATUS_CONFIG[plan.status];
  const raceDate = parseISO(plan.goal.raceDate);
  const weeksUntilRace = differenceInWeeks(raceDate, new Date());

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Link href="/plans" className="hover:text-gray-300">
          Plans
        </Link>
        <span>/</span>
        <span className="text-gray-300">{plan.name}</span>
      </div>

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-100">{plan.name}</h1>
            <span
              className={clsx(
                'px-3 py-1 rounded-full text-sm font-medium border',
                statusConfig.bgColor,
                statusConfig.color,
                statusConfig.borderColor
              )}
            >
              {statusConfig.label}
            </span>
          </div>
          {plan.description && (
            <p className="text-gray-400 mt-1">{plan.description}</p>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-wrap gap-2">
          {plan.status === 'draft' && (
            <button
              onClick={handleActivate}
              disabled={activateMutation.isPending}
              className="px-4 py-2 bg-teal-600 text-white font-medium rounded-lg hover:bg-teal-500 disabled:opacity-50 transition-colors"
            >
              {activateMutation.isPending ? 'Activating...' : 'Activate Plan'}
            </button>
          )}
          {plan.status === 'active' && (
            <>
              <button
                onClick={handlePause}
                disabled={pauseMutation.isPending}
                className="px-4 py-2 bg-amber-600 text-white font-medium rounded-lg hover:bg-amber-500 disabled:opacity-50 transition-colors"
              >
                Pause
              </button>
              <button
                onClick={() => setShowAdaptModal(true)}
                disabled={adaptMutation.isPending}
                className="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-500 disabled:opacity-50 transition-colors"
              >
                Adapt Plan
              </button>
            </>
          )}
          {plan.status === 'paused' && (
            <button
              onClick={handleActivate}
              disabled={activateMutation.isPending}
              className="px-4 py-2 bg-teal-600 text-white font-medium rounded-lg hover:bg-teal-500 disabled:opacity-50 transition-colors"
            >
              Resume
            </button>
          )}
          <button
            onClick={handleDelete}
            disabled={deleteMutation.isPending}
            className="px-4 py-2 border border-red-700 text-red-400 font-medium rounded-lg hover:bg-red-900/30 disabled:opacity-50 transition-colors"
          >
            Delete
          </button>
        </div>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-3">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Goal</p>
          <p className="font-semibold text-gray-100">
            {RACE_DISTANCE_LABELS[plan.goal.raceDistance]}
          </p>
          {plan.goal.targetTime && (
            <p className="text-sm text-gray-400">
              Target: {Math.floor(plan.goal.targetTime / 3600)}h{' '}
              {Math.floor((plan.goal.targetTime % 3600) / 60)}m
            </p>
          )}
        </div>
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-3">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Race Date</p>
          <p className="font-semibold text-gray-100">
            {format(raceDate, 'MMM d, yyyy')}
          </p>
          <p className="text-sm text-gray-400">
            {weeksUntilRace > 0
              ? `${weeksUntilRace} weeks away`
              : weeksUntilRace === 0
                ? 'This week!'
                : 'Completed'}
          </p>
        </div>
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-3">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Progress</p>
          <p className="font-semibold text-gray-100">
            Week {plan.currentWeek} of {plan.totalWeeks}
          </p>
          <p className="text-sm text-gray-400">
            {Math.round((plan.currentWeek / plan.totalWeeks) * 100)}% complete
          </p>
        </div>
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-3">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Compliance</p>
          <p className="font-semibold text-gray-100">
            {plan.compliance.compliancePercentage}%
          </p>
          <p className="text-sm text-gray-400">
            {plan.compliance.completedSessions}/{plan.compliance.totalSessions} sessions
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-800">
        {(['calendar', 'progress', 'settings'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={clsx(
              'px-4 py-2 text-sm font-medium border-b-2 transition-colors capitalize',
              activeTab === tab
                ? 'border-teal-500 text-teal-400'
                : 'border-transparent text-gray-500 hover:text-gray-300 hover:border-gray-700'
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === 'calendar' && (
        <PlanCalendar
          plan={plan}
          onSessionComplete={handleCompleteSession}
          onSessionSkip={handleSkipSession}
          onSessionClick={handleSessionClick}
        />
      )}

      {activeTab === 'progress' && <PlanProgress plan={plan} />}

      {activeTab === 'settings' && (
        <div className="space-y-6">
          {/* Plan details */}
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
            <h3 className="text-lg font-semibold text-gray-100 mb-4">
              Plan Configuration
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-2">Goal</h4>
                <dl className="space-y-2">
                  <div className="flex justify-between">
                    <dt className="text-gray-400">Distance</dt>
                    <dd className="font-medium text-gray-100">
                      {RACE_DISTANCE_LABELS[plan.goal.raceDistance]}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-400">Race Date</dt>
                    <dd className="font-medium text-gray-100">
                      {format(raceDate, 'MMMM d, yyyy')}
                    </dd>
                  </div>
                  {plan.goal.raceName && (
                    <div className="flex justify-between">
                      <dt className="text-gray-400">Race Name</dt>
                      <dd className="font-medium text-gray-100">
                        {plan.goal.raceName}
                      </dd>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <dt className="text-gray-400">Priority</dt>
                    <dd className="font-medium text-gray-100">
                      {plan.goal.priority} Goal
                    </dd>
                  </div>
                </dl>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-2">
                  Training Settings
                </h4>
                <dl className="space-y-2">
                  <div className="flex justify-between">
                    <dt className="text-gray-400">Days per Week</dt>
                    <dd className="font-medium text-gray-100">
                      {plan.constraints.daysPerWeek}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-400">Max Session</dt>
                    <dd className="font-medium text-gray-100">
                      {plan.constraints.maxSessionDuration} min
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-400">Periodization</dt>
                    <dd className="font-medium text-gray-100 capitalize">
                      {plan.periodizationType}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-400">Fitness Level</dt>
                    <dd className="font-medium text-gray-100 capitalize">
                      {plan.constraints.currentFitnessLevel}
                    </dd>
                  </div>
                </dl>
              </div>
            </div>
          </div>

          {/* Danger zone */}
          <div className="bg-red-900/20 rounded-xl border border-red-800 p-6">
            <h3 className="text-lg font-semibold text-red-400 mb-4">
              Danger Zone
            </h3>
            <p className="text-sm text-red-300/80 mb-4">
              Deleting a plan is permanent and cannot be undone.
            </p>
            <button
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="px-4 py-2 bg-red-600 text-white font-medium rounded-lg hover:bg-red-500 disabled:opacity-50 transition-colors"
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete Plan'}
            </button>
          </div>
        </div>
      )}

      {/* Session detail modal */}
      {selectedSession && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-gray-900 rounded-xl border border-gray-800 max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-100">
                  Session Details
                </h3>
                <button
                  onClick={() => setSelectedSession(null)}
                  className="p-1 hover:bg-gray-800 rounded-lg transition-colors"
                >
                  <svg
                    className="w-5 h-5 text-gray-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>

              <SessionCard
                session={selectedSession}
                onComplete={
                  selectedSession.completionStatus === 'pending'
                    ? handleCompleteSession
                    : undefined
                }
                onSkip={
                  selectedSession.completionStatus === 'pending'
                    ? handleSkipSession
                    : undefined
                }
              />
            </div>
          </div>
        </div>
      )}

      {/* Adapt plan modal */}
      {showAdaptModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-gray-900 rounded-xl border border-gray-800 max-w-md w-full">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4">
                Adapt Training Plan
              </h3>
              <p className="text-sm text-gray-400 mb-4">
                AI will regenerate the remaining weeks of your plan based on your
                progress and any changes in circumstances.
              </p>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Reason for adaptation (optional)
                </label>
                <textarea
                  value={adaptReason}
                  onChange={(e) => setAdaptReason(e.target.value)}
                  placeholder="e.g., Had an injury, missed several weeks, feeling undertrained..."
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 resize-none"
                  rows={3}
                />
              </div>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => {
                    setShowAdaptModal(false);
                    setAdaptReason('');
                  }}
                  className="px-4 py-2 text-gray-400 hover:text-gray-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAdapt}
                  disabled={adaptMutation.isPending}
                  className="px-4 py-2 bg-teal-600 text-white font-medium rounded-lg hover:bg-teal-500 disabled:opacity-50 transition-colors"
                >
                  {adaptMutation.isPending ? 'Adapting...' : 'Adapt Plan'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
