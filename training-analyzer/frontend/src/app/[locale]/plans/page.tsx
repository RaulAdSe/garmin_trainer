'use client';

import { useState, useRef, useEffect } from 'react';
import { Link } from '@/i18n/navigation';
import { clsx } from 'clsx';
import { format, parseISO } from 'date-fns';
import { usePlansList, useDeletePlan, useActivatePlan, usePausePlan } from '@/hooks/usePlans';
import { useUserProgress } from '@/hooks/useAchievements';
import { LockedFeatureGate, FEATURE_UNLOCK_LEVELS } from '@/components/gamification/LockedFeatureGate';
import type { PlanSummary, TrainingPlan } from '@/lib/types';

const TRAINING_PLANS_LEVEL = FEATURE_UNLOCK_LEVELS.training_plans; // Level 10

const STATUS_STYLES: Record<TrainingPlan['status'], { border: string; text: string }> = {
  draft: { border: 'border-l-gray-500', text: 'text-gray-400' },
  active: { border: 'border-l-green-500', text: 'text-green-400' },
  completed: { border: 'border-l-blue-500', text: 'text-blue-400' },
  paused: { border: 'border-l-amber-500', text: 'text-amber-400' },
  cancelled: { border: 'border-l-red-500', text: 'text-red-400' },
};

const DISTANCE_LABELS: Record<string, string> = {
  '5k': '5K', '10k': '10K', half_marathon: 'Half Marathon',
  marathon: 'Marathon', ultra: 'Ultra', custom: 'Custom',
};

function ActionMenu({ plan, onClose }: { plan: PlanSummary; onClose: () => void }) {
  const menuRef = useRef<HTMLDivElement>(null);
  const deleteMutation = useDeletePlan();
  const activateMutation = useActivatePlan();
  const pauseMutation = usePausePlan();

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  const handleAction = async (action: () => Promise<unknown>) => {
    await action();
    onClose();
  };

  return (
    <div ref={menuRef} className="absolute right-2 top-2 z-10 bg-gray-800 border border-gray-700 rounded-lg shadow-xl py-1 min-w-[140px]">
      {(plan.status === 'draft' || plan.status === 'paused') && (
        <button onClick={() => handleAction(() => activateMutation.mutateAsync(plan.id))}
          className="w-full px-4 py-2 text-left text-sm text-green-400 hover:bg-gray-700">
          {plan.status === 'paused' ? 'Resume' : 'Activate'}
        </button>
      )}
      {plan.status === 'active' && (
        <button onClick={() => handleAction(() => pauseMutation.mutateAsync(plan.id))}
          className="w-full px-4 py-2 text-left text-sm text-amber-400 hover:bg-gray-700">Pause</button>
      )}
      <button onClick={() => { if (confirm('Delete this plan?')) handleAction(() => deleteMutation.mutateAsync(plan.id)); }}
        className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-gray-700">Delete</button>
    </div>
  );
}

function PlanCard({ plan }: { plan: PlanSummary }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const style = STATUS_STYLES[plan.status];

  return (
    <div className="relative group">
      <Link href={`/plans/${plan.id}`}
        className={clsx(
          'block bg-gray-900 rounded-xl border border-gray-800 border-l-4 p-5',
          'hover:bg-gray-800/50 hover:border-gray-700 transition-all',
          style.border
        )}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h3 className="font-semibold text-gray-100 truncate group-hover:text-teal-400 transition-colors">
              {plan.name}
            </h3>
            <p className="text-lg font-medium text-gray-300 mt-1">
              {DISTANCE_LABELS[plan.goal.raceDistance] || plan.goal.raceDistance}
            </p>
          </div>
          <span className={clsx('text-xs font-medium uppercase tracking-wide', style.text)}>
            {plan.status}
          </span>
        </div>
        <p className="text-sm text-gray-500 mt-3">
          {format(parseISO(plan.goal.raceDate), 'MMMM d, yyyy')}
        </p>
      </Link>

      <button onClick={(e) => { e.preventDefault(); setMenuOpen(!menuOpen); }}
        className="absolute right-3 top-3 p-1.5 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-gray-700 transition-all"
        aria-label="Plan actions">
        <svg className="w-5 h-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
          <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
        </svg>
      </button>

      {menuOpen && <ActionMenu plan={plan} onClose={() => setMenuOpen(false)} />}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-4">
      <div className="w-20 h-20 bg-gradient-to-br from-teal-500/20 to-teal-600/10 rounded-2xl flex items-center justify-center mb-6">
        <svg className="w-10 h-10 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
        </svg>
      </div>
      <h3 className="text-xl font-semibold text-gray-100 mb-2">Start your first plan</h3>
      <p className="text-gray-400 text-center max-w-sm mb-8">
        Create an AI-powered training plan tailored to your goals and schedule.
      </p>
      <Link href="/plans/new"
        className="px-6 py-3 bg-teal-600 text-white font-medium rounded-xl hover:bg-teal-500 transition-colors">
        Create Plan
      </Link>
    </div>
  );
}

export default function PlansPage() {
  const [filter, setFilter] = useState<'active' | 'all'>('all');
  const { data, isLoading, error } = usePlansList({
    status: filter === 'active' ? 'active' : undefined,
    sortBy: 'startDate',
    sortOrder: 'desc',
  });
  const { data: userProgress, isLoading: progressLoading } = useUserProgress();

  const plans = data?.items || [];
  const currentLevel = userProgress?.level.level ?? 1;
  const currentXP = userProgress?.totalXp;

  // Show loading state if progress is still loading
  if (progressLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="h-8 w-48 skeleton rounded" />
          <div className="h-10 w-32 skeleton rounded" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-gray-900 rounded-xl border border-gray-800 p-5 space-y-3">
              <div className="h-5 skeleton rounded w-3/4" />
              <div className="h-6 skeleton rounded w-1/2" />
              <div className="h-4 skeleton rounded w-2/3" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <LockedFeatureGate
      feature="training_plans"
      currentLevel={currentLevel}
      requiredLevel={TRAINING_PLANS_LEVEL}
      currentXP={currentXP}
    >
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-100">Training Plans</h1>
          <Link href="/plans/new"
            className="inline-flex items-center gap-2 px-4 py-2 bg-teal-600 text-white font-medium rounded-lg hover:bg-teal-500 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            New Plan
          </Link>
        </div>

        <div className="flex gap-2">
          {(['all', 'active'] as const).map((f) => (
            <button key={f} onClick={() => setFilter(f)}
              className={clsx('px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                filter === f ? 'bg-teal-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700')}>
              {f === 'all' ? 'All Plans' : 'Active'}
            </button>
          ))}
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-gray-900 rounded-xl border border-gray-800 p-5 space-y-3">
                <div className="h-5 skeleton rounded w-3/4" />
                <div className="h-6 skeleton rounded w-1/2" />
                <div className="h-4 skeleton rounded w-2/3" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="bg-red-900/30 border border-red-800 rounded-xl p-6 text-center">
            <p className="text-red-400">Failed to load plans</p>
          </div>
        ) : plans.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {plans.map((plan) => <PlanCard key={plan.id} plan={plan} />)}
          </div>
        )}
      </div>
    </LockedFeatureGate>
  );
}
