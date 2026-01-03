'use client';

import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import { Tooltip } from './Tooltip';

export interface DataFreshnessIndicatorProps {
  /** The last sync time, or null if never synced */
  lastSyncTime: Date | null;
  /** Human-readable relative time string (e.g., "2h ago") */
  relativeTimeString: string;
  /** Callback when refresh button is clicked */
  onRefresh?: () => void;
  /** Whether a refresh is currently in progress */
  isRefreshing?: boolean;
  /** Whether the user has credentials to refresh */
  canRefresh?: boolean;
  /** Hours after which data is considered stale/yellow (default: 72 = 3 days) */
  staleThresholdHours?: number;
  /** Hours after which data is considered critical/red (default: 168 = 7 days) */
  criticalThresholdHours?: number;
  /** Additional CSS classes */
  className?: string;
  /** Show in compact mode (icon only when not stale) */
  compact?: boolean;
  /** Show pull-to-refresh hint on mobile */
  showPullHint?: boolean;
}

/**
 * Data freshness indicator component that shows when data was last synced
 * and provides a refresh button with loading state and stale data warning.
 */
export type FreshnessStatus = 'fresh' | 'stale' | 'critical' | 'never';

export function DataFreshnessIndicator({
  lastSyncTime,
  relativeTimeString,
  onRefresh,
  isRefreshing = false,
  canRefresh = true,
  staleThresholdHours = 72,
  criticalThresholdHours = 168,
  className,
  compact = false,
  showPullHint = false,
}: DataFreshnessIndicatorProps) {
  const t = useTranslations('dataFreshness');

  // Calculate freshness status
  const getFreshnessStatus = (): FreshnessStatus => {
    if (!lastSyncTime) return 'never';

    const hoursSinceSync = (Date.now() - lastSyncTime.getTime()) / (60 * 60 * 1000);

    if (hoursSinceSync >= criticalThresholdHours) return 'critical';
    if (hoursSinceSync >= staleThresholdHours) return 'stale';
    return 'fresh';
  };

  const freshnessStatus = getFreshnessStatus();
  const isStale = freshnessStatus === 'stale' || freshnessStatus === 'critical';
  const isCritical = freshnessStatus === 'critical' || freshnessStatus === 'never';

  // Determine status color - yellow for stale (3 days), red for critical (7 days)
  const statusColor = isCritical
    ? 'text-red-400'
    : isStale
    ? 'text-amber-400'
    : 'text-gray-300'; // Changed from text-gray-400 for better contrast

  const tooltipContent = (
    <div className="max-w-xs space-y-1">
      <p className="font-medium text-gray-100">{t('lastSync')}</p>
      <p className="text-gray-200">
        {lastSyncTime
          ? lastSyncTime.toLocaleString()
          : t('neverSynced')}
      </p>
      {isCritical && (
        <p className="text-red-300 text-xs mt-2">
          {t('criticalWarning', { hours: criticalThresholdHours })}
        </p>
      )}
      {isStale && !isCritical && (
        <p className="text-amber-300 text-xs mt-2">
          {t('staleWarning', { hours: staleThresholdHours })}
        </p>
      )}
      {!canRefresh && (
        <p className="text-gray-300 text-xs mt-2">
          {t('connectToSync')}
        </p>
      )}
      {showPullHint && canRefresh && (
        <p className="text-teal-300 text-xs mt-2 md:hidden">
          {t('pullToRefreshHint')}
        </p>
      )}
    </div>
  );

  // Compact mode: only show icon when not stale, full indicator when stale
  if (compact && !isStale && !isRefreshing) {
    return (
      <Tooltip content={tooltipContent} position="bottom">
        <button
          onClick={onRefresh}
          disabled={!canRefresh || isRefreshing}
          className={cn(
            'inline-flex items-center justify-center',
            'p-1.5 rounded-md transition-all duration-200',
            'text-gray-400 hover:text-gray-200 hover:bg-gray-800',
            'focus:outline-none focus:ring-2 focus:ring-teal-500/40',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            className
          )}
          aria-label={t('refresh')}
        >
          <RefreshIcon className="w-4 h-4" />
        </button>
      </Tooltip>
    );
  }

  return (
    <Tooltip content={tooltipContent} position="bottom">
      <div
        className={cn(
          'inline-flex items-center gap-2',
          'text-sm',
          className
        )}
      >
        {/* Status indicator with pulse animation when stale */}
        <span
          className={cn(
            'inline-flex items-center gap-1.5',
            statusColor,
            isCritical && 'animate-pulse',
            isStale && !isCritical && 'animate-pulse-subtle'
          )}
          role="status"
          aria-live="polite"
          aria-label={
            isCritical
              ? t('criticalAriaLabel', { time: relativeTimeString })
              : isStale
              ? t('staleAriaLabel', { time: relativeTimeString })
              : t('freshAriaLabel', { time: relativeTimeString })
          }
        >
          {/* Clock, warning, or critical icon */}
          {isCritical ? (
            <CriticalIcon className="w-3.5 h-3.5" aria-hidden="true" />
          ) : isStale ? (
            <WarningIcon className="w-3.5 h-3.5" aria-hidden="true" />
          ) : (
            <ClockIcon className="w-3.5 h-3.5" aria-hidden="true" />
          )}
          <span className="text-xs">
            {t('updated')} {relativeTimeString}
          </span>
        </span>

        {/* Refresh button */}
        <button
          onClick={onRefresh}
          disabled={!canRefresh || isRefreshing}
          className={cn(
            'inline-flex items-center justify-center',
            'p-1 rounded transition-all duration-200',
            'text-gray-400 hover:text-teal-400 hover:bg-gray-800/50',
            'focus:outline-none focus:ring-2 focus:ring-teal-500/40',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            isRefreshing && 'animate-spin'
          )}
          aria-label={t('refresh')}
        >
          <RefreshIcon className="w-3.5 h-3.5" />
        </button>
      </div>
    </Tooltip>
  );
}

// Icon components
function RefreshIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
      />
    </svg>
  );
}

function ClockIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function WarningIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
      />
    </svg>
  );
}

function CriticalIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

export default DataFreshnessIndicator;
