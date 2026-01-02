'use client';

import { useState, type ReactNode } from 'react';
import { useTranslations } from 'next-intl';
import { clsx } from 'clsx';
import { useMileageCap, type MileageCapData } from '@/hooks/useMileageCap';
import type { MileageCapStatus } from '@/lib/types';

export interface WeeklyMileageAlertProps {
  className?: string;
  showDetails?: boolean;
  compact?: boolean;
}

// Status configuration for styling and icons
const STATUS_CONFIG: Record<
  MileageCapStatus,
  {
    icon: ReactNode;
    bgColor: string;
    borderColor: string;
    textColor: string;
    progressColor: string;
    progressBgColor: string;
  }
> = {
  safe: {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    ),
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/30',
    textColor: 'text-green-400',
    progressColor: 'bg-green-500',
    progressBgColor: 'bg-green-500/20',
  },
  warning: {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
    ),
    bgColor: 'bg-yellow-500/10',
    borderColor: 'border-yellow-500/30',
    textColor: 'text-yellow-400',
    progressColor: 'bg-yellow-500',
    progressBgColor: 'bg-yellow-500/20',
  },
  near_limit: {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
    ),
    bgColor: 'bg-orange-500/10',
    borderColor: 'border-orange-500/30',
    textColor: 'text-orange-400',
    progressColor: 'bg-orange-500',
    progressBgColor: 'bg-orange-500/20',
  },
  exceeded: {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/30',
    textColor: 'text-red-400',
    progressColor: 'bg-red-500',
    progressBgColor: 'bg-red-500/20',
  },
};

/**
 * WeeklyMileageAlert component displays the current weekly mileage cap status.
 *
 * Features:
 * - Progress bar showing % of weekly cap used
 * - Color coding: green (<70%), yellow (70-90%), orange (90-100%), red (>100%)
 * - Current vs limit display
 * - Remaining km
 * - Warning message if exceeded
 */
export function WeeklyMileageAlert({
  className,
  showDetails = true,
  compact = false,
}: WeeklyMileageAlertProps) {
  const t = useTranslations('mileageCap');
  const { data: capData, isLoading, error } = useMileageCap();

  if (isLoading) {
    return <WeeklyMileageAlertSkeleton compact={compact} />;
  }

  if (error || !capData) {
    return null; // Silently fail - don't show error state for this optional component
  }

  const status = capData.status as MileageCapStatus;
  const config = STATUS_CONFIG[status];
  const percentageUsed = Math.min(capData.percentageUsed, 100);
  const percentageOverflow = capData.percentageUsed > 100 ? capData.percentageUsed - 100 : 0;

  if (compact) {
    return (
      <div
        className={clsx(
          'flex items-center gap-3 p-3 rounded-lg border',
          config.bgColor,
          config.borderColor,
          className
        )}
      >
        <div className={clsx('flex-shrink-0', config.textColor)}>{config.icon}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-gray-200">
              {t('weeklyProgress')}
            </span>
            <span className={clsx('text-sm font-medium', config.textColor)}>
              {capData.percentageUsed.toFixed(0)}%
            </span>
          </div>
          <div className={clsx('h-1.5 rounded-full overflow-hidden', config.progressBgColor)}>
            <div
              className={clsx('h-full rounded-full transition-all duration-500', config.progressColor)}
              style={{ width: `${percentageUsed}%` }}
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={clsx(
        'p-4 rounded-xl border',
        config.bgColor,
        config.borderColor,
        className
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={clsx('flex-shrink-0 p-2 rounded-lg', config.bgColor, config.textColor)}>
            {config.icon}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-200">{t('title')}</h3>
            <p className={clsx('text-xs', config.textColor)}>{t(`status.${status}`)}</p>
          </div>
        </div>
        <div className="text-right">
          <div className={clsx('text-lg font-bold', config.textColor)}>
            {capData.currentWeekKm.toFixed(1)} <span className="text-sm font-normal">km</span>
          </div>
          <div className="text-xs text-gray-400">
            {t('of')} {capData.weeklyLimitKm.toFixed(1)} km
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className={clsx('h-3 rounded-full overflow-hidden', config.progressBgColor)}>
          <div
            className={clsx(
              'h-full rounded-full transition-all duration-700 ease-out',
              config.progressColor
            )}
            style={{ width: `${percentageUsed}%` }}
          />
        </div>
        <div className="flex justify-between mt-1.5 text-xs text-gray-400">
          <span>0%</span>
          <span
            className={clsx(
              'font-medium',
              capData.percentageUsed >= 70 ? config.textColor : 'text-gray-300'
            )}
          >
            {capData.percentageUsed.toFixed(0)}%
          </span>
          <span>100%</span>
        </div>
      </div>

      {/* Stats */}
      {showDetails && (
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="text-center">
            <div className="text-lg font-semibold text-gray-200">
              {capData.previousWeekKm.toFixed(1)}
            </div>
            <div className="text-xs text-gray-400">{t('lastWeek')}</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-semibold text-gray-200">
              {capData.weeklyLimitKm.toFixed(1)}
            </div>
            <div className="text-xs text-gray-400">{t('limit')}</div>
          </div>
          <div className="text-center">
            <div className={clsx('text-lg font-semibold', config.textColor)}>
              {capData.remainingKm.toFixed(1)}
            </div>
            <div className="text-xs text-gray-400">{t('remaining')}</div>
          </div>
        </div>
      )}

      {/* Recommendation */}
      <div
        className={clsx(
          'p-3 rounded-lg text-sm',
          status === 'exceeded' ? 'bg-red-500/10 border border-red-500/20' : 'bg-gray-800/50'
        )}
      >
        <p className="text-gray-300">{capData.recommendation}</p>
      </div>

      {/* 10% Rule Info Link */}
      <div className="mt-3 flex justify-end">
        <a
          href="#ten-percent-rule"
          className={clsx(
            'text-xs hover:underline flex items-center gap-1',
            config.textColor
          )}
        >
          {t('learnAboutRule')}
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </a>
      </div>
    </div>
  );
}

/**
 * Skeleton loader for WeeklyMileageAlert
 */
export function WeeklyMileageAlertSkeleton({ compact = false }: { compact?: boolean }) {
  if (compact) {
    return (
      <div className="flex items-center gap-3 p-3 rounded-lg border border-gray-700 bg-gray-800/50 animate-pulse">
        <div className="w-5 h-5 rounded bg-gray-700" />
        <div className="flex-1">
          <div className="flex justify-between mb-1">
            <div className="h-4 w-24 rounded bg-gray-700" />
            <div className="h-4 w-10 rounded bg-gray-700" />
          </div>
          <div className="h-1.5 rounded-full bg-gray-700" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 rounded-xl border border-gray-700 bg-gray-800/50 animate-pulse">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gray-700" />
          <div>
            <div className="h-4 w-32 rounded bg-gray-700 mb-1" />
            <div className="h-3 w-20 rounded bg-gray-700" />
          </div>
        </div>
        <div className="text-right">
          <div className="h-6 w-20 rounded bg-gray-700 mb-1" />
          <div className="h-3 w-16 rounded bg-gray-700" />
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="h-3 rounded-full bg-gray-700" />
        <div className="flex justify-between mt-1.5">
          <div className="h-3 w-6 rounded bg-gray-700" />
          <div className="h-3 w-10 rounded bg-gray-700" />
          <div className="h-3 w-8 rounded bg-gray-700" />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="text-center">
            <div className="h-6 w-12 mx-auto rounded bg-gray-700 mb-1" />
            <div className="h-3 w-16 mx-auto rounded bg-gray-700" />
          </div>
        ))}
      </div>

      {/* Recommendation */}
      <div className="p-3 rounded-lg bg-gray-700/50">
        <div className="h-4 w-full rounded bg-gray-700 mb-1" />
        <div className="h-4 w-3/4 rounded bg-gray-700" />
      </div>
    </div>
  );
}

export default WeeklyMileageAlert;
