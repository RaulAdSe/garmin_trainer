'use client';

import { useState } from 'react';
import Link from 'next/link';
import { clsx } from 'clsx';
import { format, parseISO, differenceInWeeks, isAfter } from 'date-fns';
import { usePlansList, useDeletePlan, useActivatePlan, usePausePlan } from '@/hooks/usePlans';
import type { PlanSummary, TrainingPlan } from '@/lib/types';

const STATUS_CONFIG: Record<
  TrainingPlan['status'],
  { label: string; color: string; bgColor: string }
> = {
  draft: {
    label: 'Draft',
    color: 'text-gray-400',
    bgColor: 'bg-gray-800',
  },
  active: {
    label: 'Active',
    color: 'text-green-400',
    bgColor: 'bg-green-900/50',
  },
  completed: {
    label: 'Completed',
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/50',
  },
  paused: {
    label: 'Paused',
    color: 'text-amber-400',
    bgColor: 'bg-amber-900/50',
  },
  cancelled: {
    label: 'Cancelled',
    color: 'text-red-400',
    bgColor: 'bg-red-900/50',
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

function PlanCard({ plan }: { plan: PlanSummary }) {
  const statusConfig = STATUS_CONFIG[plan.status];
  const raceDate = parseISO(plan.goal.raceDate);
  const weeksUntilRace = differenceInWeeks(raceDate, new Date());
  const isRacePast = !isAfter(raceDate, new Date());

  const deleteMutation = useDeletePlan();
  const activateMutation = useActivatePlan();
  const pauseMutation = usePausePlan();

  const handleDelete = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this plan?')) {
      await deleteMutation.mutateAsync(plan.id);
    }
  };

  const handleActivate = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    await activateMutation.mutateAsync(plan.id);
  };

  const handlePause = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    await pauseMutation.mutateAsync(plan.id);
  };

  return (
    <Link
      href={`/plans/${plan.id}`}
      className="block bg-gray-900 rounded-xl border border-gray-800 overflow-hidden hover:border-gray-700 hover:shadow-lg transition-all group card-hover"
    >
      {/* Header with status */}
      <div className="px-6 py-4 border-b border-gray-800">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-lg text-gray-100 truncate group-hover:text-teal-400 transition-colors">
              {plan.name}
            </h3>
            <div className="flex items-center gap-2 mt-1">
              <span
                className={clsx(
                  'text-xs px-2 py-0.5 rounded-full font-medium',
                  statusConfig.bgColor,
                  statusConfig.color
                )}
              >
                {statusConfig.label}
              </span>
              <span className="text-sm text-gray-500">
                Week {plan.currentWeek} of {plan.totalWeeks}
              </span>
            </div>
          </div>

          {/* Priority badge */}
          <span
            className={clsx(
              'px-2 py-1 rounded-lg text-xs font-bold',
              plan.goal.priority === 'A'
                ? 'bg-red-900/50 text-red-400'
                : plan.goal.priority === 'B'
                  ? 'bg-yellow-900/50 text-yellow-400'
                  : 'bg-gray-800 text-gray-400'
            )}
          >
            {plan.goal.priority} Goal
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="px-6 py-4">
        <div className="grid grid-cols-2 gap-4">
          {/* Race Info */}
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Race</p>
            <p className="font-semibold text-gray-100">
              {RACE_DISTANCE_LABELS[plan.goal.raceDistance] || plan.goal.raceDistance}
            </p>
            <p className="text-sm text-gray-400">
              {format(raceDate, 'MMM d, yyyy')}
            </p>
          </div>

          {/* Time until race */}
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">
              {isRacePast ? 'Race was' : 'Race in'}
            </p>
            <p
              className={clsx(
                'font-semibold',
                isRacePast
                  ? 'text-gray-500'
                  : weeksUntilRace <= 2
                    ? 'text-red-400'
                    : weeksUntilRace <= 4
                      ? 'text-amber-400'
                      : 'text-gray-100'
              )}
            >
              {isRacePast
                ? 'Completed'
                : weeksUntilRace <= 0
                  ? 'This week!'
                  : `${weeksUntilRace} week${weeksUntilRace === 1 ? '' : 's'}`}
            </p>
          </div>
        </div>

        {/* Compliance bar */}
        <div className="mt-4">
          <div className="flex items-center justify-between text-sm mb-1">
            <span className="text-gray-500">Compliance</span>
            <span className="font-medium text-gray-100">
              {plan.compliancePercentage}%
            </span>
          </div>
          <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className={clsx(
                'h-full rounded-full transition-all',
                plan.compliancePercentage >= 80
                  ? 'bg-teal-500'
                  : plan.compliancePercentage >= 60
                    ? 'bg-yellow-500'
                    : 'bg-red-500'
              )}
              style={{ width: `${plan.compliancePercentage}%` }}
            />
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="px-6 py-3 bg-gray-800/50 border-t border-gray-800 flex justify-between items-center">
        <div className="flex gap-2">
          {plan.status === 'draft' && (
            <button
              onClick={handleActivate}
              disabled={activateMutation.isPending}
              className="text-sm text-teal-400 hover:text-teal-300 font-medium"
            >
              Activate
            </button>
          )}
          {plan.status === 'active' && (
            <button
              onClick={handlePause}
              disabled={pauseMutation.isPending}
              className="text-sm text-amber-400 hover:text-amber-300 font-medium"
            >
              Pause
            </button>
          )}
          {plan.status === 'paused' && (
            <button
              onClick={handleActivate}
              disabled={activateMutation.isPending}
              className="text-sm text-teal-400 hover:text-teal-300 font-medium"
            >
              Resume
            </button>
          )}
        </div>
        <button
          onClick={handleDelete}
          disabled={deleteMutation.isPending}
          className="text-sm text-red-400 hover:text-red-300"
        >
          Delete
        </button>
      </div>
    </Link>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-16 px-4">
      <div className="w-16 h-16 bg-teal-900/50 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg
          className="w-8 h-8 text-teal-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
          />
        </svg>
      </div>
      <h3 className="text-xl font-semibold text-gray-100 mb-2">
        No training plans yet
      </h3>
      <p className="text-gray-400 mb-6 max-w-md mx-auto">
        Create your first AI-powered training plan to start working toward your
        running goals.
      </p>
      <Link
        href="/plans/new"
        className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 text-white font-medium rounded-lg hover:bg-teal-500 transition-colors"
      >
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 4v16m8-8H4"
          />
        </svg>
        Create Your First Plan
      </Link>
    </div>
  );
}

export default function PlansPage() {
  const [statusFilter, setStatusFilter] = useState<TrainingPlan['status'] | 'all'>('all');

  const {
    data: plansResponse,
    isLoading,
    error,
  } = usePlansList({
    status: statusFilter === 'all' ? undefined : statusFilter,
    sortBy: 'startDate',
    sortOrder: 'desc',
  });

  const plans = plansResponse?.items || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Training Plans</h1>
          <p className="text-gray-400 mt-1">
            Manage your AI-generated training plans
          </p>
        </div>
        <Link
          href="/plans/new"
          className="inline-flex items-center gap-2 px-4 py-2 bg-teal-600 text-white font-medium rounded-lg hover:bg-teal-500 transition-colors"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          New Plan
        </Link>
      </div>

      {/* Filters */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {(['all', 'active', 'draft', 'paused', 'completed'] as const).map((status) => (
          <button
            key={status}
            onClick={() => setStatusFilter(status)}
            className={clsx(
              'px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors',
              statusFilter === status
                ? 'bg-teal-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-300'
            )}
          >
            {status === 'all' ? 'All Plans' : STATUS_CONFIG[status].label}
          </button>
        ))}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="bg-gray-900 rounded-xl border border-gray-800 h-64"
            >
              <div className="p-6 space-y-4">
                <div className="h-6 skeleton rounded w-3/4" />
                <div className="h-4 skeleton rounded w-1/2" />
                <div className="h-20 skeleton rounded" />
              </div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="bg-red-900/30 border border-red-800 rounded-xl p-6 text-center">
          <p className="text-red-400 font-medium">Failed to load plans</p>
          <p className="text-red-500 text-sm mt-1">
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      ) : plans.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {plans.map((plan) => (
            <PlanCard key={plan.id} plan={plan} />
          ))}
        </div>
      )}

      {/* Pagination info */}
      {plansResponse && plansResponse.total > 0 && (
        <div className="mt-8 text-center text-sm text-gray-500">
          Showing {plans.length} of {plansResponse.total} plans
        </div>
      )}
    </div>
  );
}
