'use client';

import { useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/Card';

// Icons
const IconBatteryLow = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <rect width="16" height="10" x="2" y="7" rx="2" ry="2" />
    <line x1="22" x2="22" y1="11" y2="13" />
    <line x1="6" x2="6" y1="11" y2="13" />
  </svg>
);

const IconX = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M18 6 6 18" />
    <path d="m6 6 12 12" />
  </svg>
);

const IconBed = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M2 4v16" />
    <path d="M2 8h18a2 2 0 0 1 2 2v10" />
    <path d="M2 17h20" />
    <path d="M6 8v9" />
  </svg>
);

const IconDroplet = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z" />
  </svg>
);

const IconActivity = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2" />
  </svg>
);

const IconUtensils = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2" />
    <path d="M7 2v20" />
    <path d="M21 15V2v0a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7" />
  </svg>
);

interface RecoverySupportProps {
  readinessScore: number;
  onDismiss?: () => void;
  className?: string;
}

const ALTERNATIVE_ACTIVITIES = [
  { key: 'yoga', label: 'emotional.activities.yoga' },
  { key: 'walking', label: 'emotional.activities.easyWalking' },
  { key: 'stretching', label: 'emotional.activities.stretching' },
  { key: 'meditation', label: 'emotional.activities.meditation' },
  { key: 'foamRolling', label: 'emotional.activities.foamRolling' },
  { key: 'swimming', label: 'emotional.activities.easySwim' },
];

const RECOVERY_TIPS = [
  { icon: IconBed, label: 'emotional.recovery.prioritizeSleep' },
  { icon: IconDroplet, label: 'emotional.recovery.stayHydrated' },
  { icon: IconUtensils, label: 'emotional.recovery.nutrition' },
  { icon: IconActivity, label: 'emotional.recovery.lightMovement' },
];

export function RecoverySupport({
  readinessScore,
  onDismiss,
  className,
}: RecoverySupportProps) {
  const t = useTranslations();
  const [isVisible, setIsVisible] = useState(true);
  const [isAnimatingOut, setIsAnimatingOut] = useState(false);
  const [showAllActivities, setShowAllActivities] = useState(false);

  const handleDismiss = useCallback(() => {
    setIsAnimatingOut(true);
    setTimeout(() => {
      setIsVisible(false);
      onDismiss?.();
    }, 200);
  }, [onDismiss]);

  if (!isVisible) return null;

  // Determine severity based on readiness score
  const isRedZone = readinessScore < 40;
  const severityColor = isRedZone ? 'text-red-400' : 'text-amber-400';
  const severityBg = isRedZone ? 'bg-red-900/20' : 'bg-amber-900/20';
  const severityBorder = isRedZone ? 'border-red-700/50' : 'border-amber-700/50';

  const displayedActivities = showAllActivities
    ? ALTERNATIVE_ACTIVITIES
    : ALTERNATIVE_ACTIVITIES.slice(0, 4);

  return (
    <Card
      padding="md"
      className={cn(
        'relative overflow-hidden transition-all duration-200',
        severityBg,
        severityBorder,
        'border',
        isAnimatingOut && 'opacity-0 transform translate-y-2',
        'animate-in fade-in slide-in-from-bottom-2 duration-300',
        className
      )}
    >
      {/* Dismiss button */}
      <button
        onClick={handleDismiss}
        className={cn(
          'absolute top-3 right-3 p-1.5 rounded-full',
          'text-gray-400 hover:text-gray-200',
          'hover:bg-white/10 transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-white/20'
        )}
        aria-label={t('common.close')}
      >
        <IconX />
      </button>

      {/* Header */}
      <div className="flex items-start gap-4 mb-4">
        <div
          className={cn(
            'shrink-0 w-12 h-12 rounded-full flex items-center justify-center',
            'bg-white/10',
            severityColor
          )}
        >
          <IconBatteryLow />
        </div>
        <div className="pr-6">
          <h3 className={cn('font-semibold mb-1', severityColor)}>
            {t('emotional.recovery.title')}
          </h3>
          <p className="text-sm text-gray-300">
            {t('emotional.recovery.bodyAskingRest')}
          </p>
        </div>
      </div>

      {/* Readiness indicator */}
      <div className="mb-4 p-3 rounded-lg bg-black/20">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-gray-400">
            {t('emotional.recovery.readinessScore')}
          </span>
          <span className={cn('text-sm font-semibold', severityColor)}>
            {Math.round(readinessScore)}%
          </span>
        </div>
        <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
          <div
            className={cn(
              'h-full rounded-full transition-all duration-500',
              isRedZone
                ? 'bg-gradient-to-r from-red-600 to-red-400'
                : 'bg-gradient-to-r from-amber-600 to-amber-400'
            )}
            style={{ width: `${readinessScore}%` }}
          />
        </div>
        <p className="text-xs text-gray-500 mt-1">
          {isRedZone
            ? t('emotional.recovery.redZoneMessage')
            : t('emotional.recovery.yellowZoneMessage')}
        </p>
      </div>

      {/* Recovery tips */}
      <div className="mb-4">
        <h4 className="text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">
          {t('emotional.recovery.tipsTitle')}
        </h4>
        <div className="grid grid-cols-2 gap-2">
          {RECOVERY_TIPS.map((tip) => {
            const Icon = tip.icon;
            return (
              <div
                key={tip.label}
                className={cn(
                  'flex items-center gap-2 p-2 rounded-lg',
                  'bg-white/5 border border-white/5'
                )}
              >
                <Icon />
                <span className="text-xs text-gray-300">
                  {t(tip.label)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Alternative activities */}
      <div>
        <h4 className="text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">
          {t('emotional.recovery.alternativeActivities')}
        </h4>
        <div className="flex flex-wrap gap-1.5">
          {displayedActivities.map((activity) => (
            <span
              key={activity.key}
              className={cn(
                'text-xs px-2.5 py-1 rounded-full',
                'bg-white/5 text-gray-300 border border-white/10',
                'hover:bg-white/10 transition-colors cursor-default'
              )}
            >
              {t(activity.label)}
            </span>
          ))}
          {!showAllActivities && ALTERNATIVE_ACTIVITIES.length > 4 && (
            <button
              onClick={() => setShowAllActivities(true)}
              className={cn(
                'text-xs px-2.5 py-1 rounded-full',
                'bg-white/5 text-gray-400 border border-white/10',
                'hover:bg-white/10 hover:text-gray-300 transition-colors'
              )}
            >
              +{ALTERNATIVE_ACTIVITIES.length - 4} {t('common.more')}
            </button>
          )}
        </div>
      </div>

      {/* Encouragement footer */}
      <p className="mt-4 text-xs text-gray-500 italic text-center">
        {t('emotional.recovery.encouragement')}
      </p>
    </Card>
  );
}

export default RecoverySupport;
