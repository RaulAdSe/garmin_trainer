'use client';

import { useState, useEffect, type ReactNode } from 'react';
import { useTranslations } from 'next-intl';
import { clsx } from 'clsx';
import {
  useMileageCapComplete,
  useTenPercentRuleInfo,
  type MileageCapData,
  type WeeklyComparisonData,
} from '@/hooks/useMileageCap';
import type { MileageCapStatus } from '@/lib/types';

export interface MileageCapCardProps {
  className?: string;
  showInfo?: boolean;
}

// Status configuration for gauge and styling
const STATUS_CONFIG: Record<
  MileageCapStatus,
  {
    color: string;
    bgColor: string;
    gaugeColor: string;
    label: string;
  }
> = {
  safe: {
    color: 'text-green-400',
    bgColor: 'bg-green-500/10',
    gaugeColor: '#22c55e',
    label: 'safe',
  },
  warning: {
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/10',
    gaugeColor: '#eab308',
    label: 'warning',
  },
  near_limit: {
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/10',
    gaugeColor: '#f97316',
    label: 'nearLimit',
  },
  exceeded: {
    color: 'text-red-400',
    bgColor: 'bg-red-500/10',
    gaugeColor: '#ef4444',
    label: 'exceeded',
  },
};

/**
 * MileageCapCard component displays a visual gauge of weekly mileage usage.
 *
 * Features:
 * - Visual gauge/meter showing progress
 * - Week-over-week comparison
 * - Smart recommendation
 * - Link to learn about 10% rule
 */
export function MileageCapCard({ className, showInfo = true }: MileageCapCardProps) {
  const t = useTranslations('mileageCap');
  const {
    capData,
    isCapLoading,
    capError,
    comparisonData,
    isComparisonLoading,
  } = useMileageCapComplete();

  const { data: ruleInfo } = useTenPercentRuleInfo();
  const [showInfoModal, setShowInfoModal] = useState(false);

  if (isCapLoading) {
    return <MileageCapCardSkeleton />;
  }

  if (capError || !capData) {
    return null;
  }

  const status = capData.status as MileageCapStatus;
  const config = STATUS_CONFIG[status];
  const percentage = Math.min(capData.percentageUsed, 100);

  return (
    <div
      className={clsx(
        'p-5 rounded-2xl bg-gray-900/50 border border-gray-800',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-100">{t('cardTitle')}</h3>
        {showInfo && (
          <button
            onClick={() => setShowInfoModal(true)}
            className="p-1.5 rounded-lg hover:bg-gray-800 transition-colors text-gray-400 hover:text-gray-200"
            title={t('learnAboutRule')}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </button>
        )}
      </div>

      {/* Gauge */}
      <div className="flex flex-col items-center mb-6">
        <MileageGauge
          percentage={capData.percentageUsed}
          status={status}
          currentKm={capData.currentWeekKm}
          limitKm={capData.weeklyLimitKm}
        />
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="text-center p-3 rounded-lg bg-gray-800/50">
          <div className="text-2xl font-bold text-gray-100">
            {capData.remainingKm.toFixed(1)}
          </div>
          <div className="text-xs text-gray-400">{t('kmRemaining')}</div>
        </div>
        <div className="text-center p-3 rounded-lg bg-gray-800/50">
          <div className={clsx('text-2xl font-bold', config.color)}>
            {capData.allowedIncreaseKm.toFixed(1)}
          </div>
          <div className="text-xs text-gray-400">{t('allowedIncrease')}</div>
        </div>
      </div>

      {/* Week-over-Week Comparison */}
      {comparisonData && (
        <WeekOverWeekComparison data={comparisonData} />
      )}

      {/* Recommendation */}
      <div
        className={clsx(
          'mt-4 p-3 rounded-xl text-sm',
          config.bgColor
        )}
      >
        <div className="flex items-start gap-2">
          <div className={clsx('mt-0.5 flex-shrink-0', config.color)}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <p className="text-gray-300">{capData.recommendation}</p>
        </div>
      </div>

      {/* Info Modal */}
      {showInfoModal && ruleInfo && (
        <TenPercentRuleModal
          info={ruleInfo}
          onClose={() => setShowInfoModal(false)}
        />
      )}
    </div>
  );
}

/**
 * Visual gauge component showing mileage usage
 */
function MileageGauge({
  percentage,
  status,
  currentKm,
  limitKm,
}: {
  percentage: number;
  status: MileageCapStatus;
  currentKm: number;
  limitKm: number;
}) {
  const t = useTranslations('mileageCap');
  const config = STATUS_CONFIG[status];
  const [animatedPercentage, setAnimatedPercentage] = useState(0);

  // Animate the gauge on mount
  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimatedPercentage(Math.min(percentage, 100));
    }, 100);
    return () => clearTimeout(timer);
  }, [percentage]);

  // SVG gauge parameters
  const radius = 60;
  const strokeWidth = 12;
  const normalizedRadius = radius - strokeWidth / 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const strokeDashoffset = circumference - (animatedPercentage / 100) * circumference;

  return (
    <div className="relative">
      <svg height={radius * 2 + 10} width={radius * 2 + 10} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          stroke="rgb(55 65 81)"
          fill="transparent"
          strokeWidth={strokeWidth}
          r={normalizedRadius}
          cx={radius + 5}
          cy={radius + 5}
        />
        {/* Progress circle */}
        <circle
          stroke={config.gaugeColor}
          fill="transparent"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset={strokeDashoffset}
          r={normalizedRadius}
          cx={radius + 5}
          cy={radius + 5}
          style={{
            transition: 'stroke-dashoffset 1s ease-out',
          }}
        />
      </svg>
      {/* Center content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className={clsx('text-3xl font-bold', config.color)}>
          {percentage.toFixed(0)}%
        </div>
        <div className="text-xs text-gray-400 mt-1">
          {currentKm.toFixed(1)} / {limitKm.toFixed(1)} km
        </div>
        <div className={clsx('text-xs font-medium mt-1', config.color)}>
          {t(`status.${status}`)}
        </div>
      </div>
    </div>
  );
}

/**
 * Week-over-week comparison component
 */
function WeekOverWeekComparison({ data }: { data: WeeklyComparisonData }) {
  const t = useTranslations('mileageCap');
  const isIncrease = data.changeKm > 0;
  const isDecrease = data.changeKm < 0;

  return (
    <div className="flex items-center justify-between p-3 rounded-lg bg-gray-800/30">
      <div className="flex items-center gap-3">
        <div className="text-sm text-gray-400">{t('weekComparison')}</div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-300">
            {data.previousWeek.totalKm.toFixed(1)}
          </span>
          <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
          </svg>
          <span className="text-sm font-medium text-gray-200">
            {data.currentWeek.totalKm.toFixed(1)}
          </span>
        </div>
      </div>
      <div
        className={clsx(
          'flex items-center gap-1 text-sm font-medium',
          isIncrease && data.changePct > 10 ? 'text-red-400' : '',
          isIncrease && data.changePct <= 10 ? 'text-green-400' : '',
          isDecrease ? 'text-blue-400' : '',
          !isIncrease && !isDecrease ? 'text-gray-400' : ''
        )}
      >
        {isIncrease ? '+' : ''}
        {data.changePct.toFixed(0)}%
        {isIncrease && (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 11l5-5m0 0l5 5m-5-5v12" />
          </svg>
        )}
        {isDecrease && (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 13l-5 5m0 0l-5-5m5 5V6" />
          </svg>
        )}
      </div>
    </div>
  );
}

/**
 * Modal showing information about the 10% rule
 */
function TenPercentRuleModal({
  info,
  onClose,
}: {
  info: { title: string; description: string; benefits: string[]; tips: string[] };
  onClose: () => void;
}) {
  const t = useTranslations('mileageCap');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-gray-900 rounded-2xl border border-gray-700 max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="p-5">
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-gray-100">{info.title}</h3>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-gray-800 transition-colors text-gray-400 hover:text-gray-200"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Description */}
          <p className="text-sm text-gray-300 mb-6">{info.description}</p>

          {/* Benefits */}
          <div className="mb-6">
            <h4 className="text-sm font-semibold text-gray-200 mb-2">{t('infoModal.benefits')}</h4>
            <ul className="space-y-2">
              {info.benefits.map((benefit, index) => (
                <li key={index} className="flex items-start gap-2 text-sm text-gray-400">
                  <svg className="w-4 h-4 mt-0.5 text-green-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  {benefit}
                </li>
              ))}
            </ul>
          </div>

          {/* Tips */}
          <div className="mb-4">
            <h4 className="text-sm font-semibold text-gray-200 mb-2">{t('infoModal.tips')}</h4>
            <ul className="space-y-2">
              {info.tips.map((tip, index) => (
                <li key={index} className="flex items-start gap-2 text-sm text-gray-400">
                  <svg className="w-4 h-4 mt-0.5 text-teal-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {tip}
                </li>
              ))}
            </ul>
          </div>

          {/* Close button */}
          <button
            onClick={onClose}
            className="w-full py-3 rounded-xl bg-teal-600 hover:bg-teal-500 transition-colors text-white font-medium"
          >
            {t('infoModal.gotIt')}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Skeleton loader for MileageCapCard
 */
export function MileageCapCardSkeleton() {
  return (
    <div className="p-5 rounded-2xl bg-gray-900/50 border border-gray-800 animate-pulse">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="h-6 w-32 rounded bg-gray-700" />
        <div className="w-5 h-5 rounded bg-gray-700" />
      </div>

      {/* Gauge placeholder */}
      <div className="flex justify-center mb-6">
        <div className="w-32 h-32 rounded-full bg-gray-700" />
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {[1, 2].map((i) => (
          <div key={i} className="p-3 rounded-lg bg-gray-800/50">
            <div className="h-8 w-16 mx-auto rounded bg-gray-700 mb-1" />
            <div className="h-3 w-20 mx-auto rounded bg-gray-700" />
          </div>
        ))}
      </div>

      {/* Comparison placeholder */}
      <div className="h-12 rounded-lg bg-gray-800/30 mb-4" />

      {/* Recommendation placeholder */}
      <div className="p-3 rounded-xl bg-gray-800/30">
        <div className="h-4 w-full rounded bg-gray-700 mb-1" />
        <div className="h-4 w-3/4 rounded bg-gray-700" />
      </div>
    </div>
  );
}

export default MileageCapCard;
