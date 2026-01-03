'use client';

import { useState, useCallback, type ReactNode } from 'react';
import { clsx } from 'clsx';
import { useActiveAlerts } from '@/hooks/useSafetyAlerts';
import type { SafetyAlert, AlertSeverity, AlertType } from '@/lib/types';
import { SAFETY_ALERT_COLORS, ALERT_TYPE_NAMES } from '@/lib/types';

// ============================================
// Icons
// ============================================

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

function InfoIcon({ className }: { className?: string }) {
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
        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function CloseIcon({ className }: { className?: string }) {
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
        d="M6 18L18 6M6 6l12 12"
      />
    </svg>
  );
}

function ChevronDownIcon({ className }: { className?: string }) {
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
        d="M19 9l-7 7-7-7"
      />
    </svg>
  );
}

function ChevronUpIcon({ className }: { className?: string }) {
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
        d="M5 15l7-7 7 7"
      />
    </svg>
  );
}

// ============================================
// Helper Functions
// ============================================

function getAlertIcon(severity: AlertSeverity): ReactNode {
  const iconClass = 'w-5 h-5 sm:w-6 sm:h-6';
  switch (severity) {
    case 'critical':
      return <CriticalIcon className={iconClass} />;
    case 'moderate':
      return <WarningIcon className={iconClass} />;
    default:
      return <InfoIcon className={iconClass} />;
  }
}

function formatMetricValue(key: string, value: number | string): string {
  if (typeof value === 'number') {
    if (key.toLowerCase().includes('pct') || key.toLowerCase().includes('percent')) {
      return `${value.toFixed(1)}%`;
    }
    if (key.toLowerCase().includes('load')) {
      return value.toFixed(0);
    }
    return value.toFixed(2);
  }
  return String(value);
}

// ============================================
// Single Alert Card
// ============================================

interface AlertCardProps {
  alert: SafetyAlert;
  onAcknowledge: (id: string) => void;
  onDismiss: (id: string) => void;
  isAcknowledging: boolean;
  isDismissing: boolean;
  compact?: boolean;
}

function AlertCard({
  alert,
  onAcknowledge,
  onDismiss,
  isAcknowledging,
  isDismissing,
  compact = false,
}: AlertCardProps) {
  const [isExpanded, setIsExpanded] = useState(!compact);
  const colors = SAFETY_ALERT_COLORS[alert.severity];

  const handleAcknowledge = useCallback(() => {
    onAcknowledge(alert.id);
  }, [alert.id, onAcknowledge]);

  const handleDismiss = useCallback(() => {
    onDismiss(alert.id);
  }, [alert.id, onDismiss]);

  if (compact && !isExpanded) {
    return (
      <div
        className={clsx(
          'flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors',
          colors.bgLight,
          colors.border,
          'hover:bg-opacity-20'
        )}
        onClick={() => setIsExpanded(true)}
      >
        <div className={colors.icon}>{getAlertIcon(alert.severity)}</div>
        <div className="flex-1 min-w-0">
          <p className={clsx('text-sm font-medium truncate', colors.text)}>
            {alert.title}
          </p>
        </div>
        <ChevronDownIcon className="w-4 h-4 text-gray-400" />
      </div>
    );
  }

  return (
    <div
      className={clsx(
        'rounded-xl border overflow-hidden',
        colors.bgLight,
        colors.border
      )}
    >
      {/* Header */}
      <div className="flex items-start gap-3 p-4">
        <div className={clsx('flex-shrink-0 mt-0.5', colors.icon)}>
          {getAlertIcon(alert.severity)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h3 className={clsx('font-semibold', colors.text)}>
                {alert.title}
              </h3>
              <p className="text-xs text-gray-400 mt-0.5">
                {ALERT_TYPE_NAMES[alert.alertType as AlertType]}
              </p>
            </div>
            {compact && (
              <button
                onClick={() => setIsExpanded(false)}
                className="text-gray-400 hover:text-gray-300 p-1"
              >
                <ChevronUpIcon className="w-4 h-4" />
              </button>
            )}
          </div>
          <p className="text-sm text-gray-300 mt-2">{alert.message}</p>
        </div>
      </div>

      {/* Metrics */}
      {Object.keys(alert.metrics).length > 0 && (
        <div className="px-4 py-2 bg-gray-800/30 border-t border-gray-700/50">
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
            {Object.entries(alert.metrics).map(([key, value]) => (
              <div key={key} className="flex items-center gap-1">
                <span className="text-gray-400">
                  {key.replace(/([A-Z])/g, ' $1').trim()}:
                </span>
                <span className={colors.text}>
                  {formatMetricValue(key, value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendation */}
      <div className="px-4 py-3 bg-gray-800/50">
        <p className="text-sm text-gray-300">
          <span className="font-medium text-gray-200">Recommendation: </span>
          {alert.recommendation}
        </p>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-gray-700/50">
        <button
          onClick={handleDismiss}
          disabled={isDismissing}
          className="px-3 py-1.5 text-sm text-gray-400 hover:text-gray-300 hover:bg-gray-700/50 rounded-lg transition-colors disabled:opacity-50"
        >
          {isDismissing ? 'Dismissing...' : 'Dismiss'}
        </button>
        <button
          onClick={handleAcknowledge}
          disabled={isAcknowledging}
          className={clsx(
            'px-3 py-1.5 text-sm font-medium rounded-lg transition-colors disabled:opacity-50',
            colors.bg,
            'text-white hover:opacity-90'
          )}
        >
          {isAcknowledging ? 'Acknowledging...' : 'Got it'}
        </button>
      </div>
    </div>
  );
}

// ============================================
// SafetyAlertBanner Component
// ============================================

export interface SafetyAlertBannerProps {
  className?: string;
  maxAlerts?: number;
  compact?: boolean;
  showWhenEmpty?: boolean;
}

/**
 * SafetyAlertBanner displays active safety alerts prominently.
 *
 * Features:
 * - Different colors for severity levels (info, moderate, critical)
 * - Dismissible with acknowledgment
 * - Shows recommendation for each alert
 * - Compact mode for space-constrained layouts
 */
export function SafetyAlertBanner({
  className,
  maxAlerts = 3,
  compact = false,
  showWhenEmpty = false,
}: SafetyAlertBannerProps) {
  const {
    alerts,
    activeCount,
    criticalCount,
    isLoading,
    acknowledge,
    dismiss,
    isAcknowledging,
    isDismissing,
  } = useActiveAlerts();

  const [showAll, setShowAll] = useState(false);

  // Don't render anything while loading or if no alerts
  if (isLoading) {
    return <SafetyAlertBannerSkeleton compact={compact} />;
  }

  // Filter to only active alerts and sort by severity
  const activeAlerts = alerts
    .filter((a) => a.status === 'active')
    .sort((a, b) => {
      const severityOrder = { critical: 0, moderate: 1, info: 2 };
      return (
        severityOrder[a.severity as keyof typeof severityOrder] -
        severityOrder[b.severity as keyof typeof severityOrder]
      );
    });

  if (activeAlerts.length === 0) {
    if (!showWhenEmpty) return null;

    return (
      <div
        className={clsx(
          'flex items-center gap-3 p-4 rounded-xl bg-green-500/10 border border-green-500/30',
          className
        )}
      >
        <svg
          className="w-5 h-5 text-green-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <span className="text-sm text-green-400">
          No active safety alerts - your training load is within safe ranges.
        </span>
      </div>
    );
  }

  const visibleAlerts = showAll ? activeAlerts : activeAlerts.slice(0, maxAlerts);
  const hiddenCount = activeAlerts.length - maxAlerts;

  return (
    <div className={clsx('space-y-3', className)}>
      {/* Summary Header for Multiple Alerts */}
      {activeAlerts.length > 1 && (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-300">
              {activeCount} Active Alert{activeCount !== 1 ? 's' : ''}
            </span>
            {criticalCount > 0 && (
              <span className="px-2 py-0.5 text-xs font-medium bg-red-500/20 text-red-400 rounded-full">
                {criticalCount} Critical
              </span>
            )}
          </div>
        </div>
      )}

      {/* Alert Cards */}
      <div className="space-y-3">
        {visibleAlerts.map((alert) => (
          <AlertCard
            key={alert.id}
            alert={alert}
            onAcknowledge={acknowledge}
            onDismiss={dismiss}
            isAcknowledging={isAcknowledging}
            isDismissing={isDismissing}
            compact={compact}
          />
        ))}
      </div>

      {/* Show More/Less */}
      {hiddenCount > 0 && !showAll && (
        <button
          onClick={() => setShowAll(true)}
          className="w-full py-2 text-sm text-gray-400 hover:text-gray-300 hover:bg-gray-800/50 rounded-lg transition-colors"
        >
          Show {hiddenCount} more alert{hiddenCount !== 1 ? 's' : ''}
        </button>
      )}
      {showAll && activeAlerts.length > maxAlerts && (
        <button
          onClick={() => setShowAll(false)}
          className="w-full py-2 text-sm text-gray-400 hover:text-gray-300 hover:bg-gray-800/50 rounded-lg transition-colors"
        >
          Show less
        </button>
      )}
    </div>
  );
}

// ============================================
// Skeleton
// ============================================

export function SafetyAlertBannerSkeleton({ compact = false }: { compact?: boolean }) {
  if (compact) {
    return (
      <div className="flex items-center gap-3 p-3 rounded-lg border border-gray-700 bg-gray-800/50 animate-pulse">
        <div className="w-5 h-5 rounded bg-gray-700" />
        <div className="flex-1">
          <div className="h-4 w-48 rounded bg-gray-700" />
        </div>
        <div className="w-4 h-4 rounded bg-gray-700" />
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-700 bg-gray-800/50 animate-pulse overflow-hidden">
      <div className="flex items-start gap-3 p-4">
        <div className="w-6 h-6 rounded bg-gray-700" />
        <div className="flex-1 space-y-2">
          <div className="h-5 w-48 rounded bg-gray-700" />
          <div className="h-3 w-24 rounded bg-gray-700" />
          <div className="h-4 w-full rounded bg-gray-700 mt-2" />
          <div className="h-4 w-3/4 rounded bg-gray-700" />
        </div>
      </div>
      <div className="px-4 py-3 bg-gray-800/50">
        <div className="h-4 w-full rounded bg-gray-700" />
      </div>
      <div className="flex justify-end gap-2 px-4 py-3 border-t border-gray-700/50">
        <div className="h-8 w-20 rounded bg-gray-700" />
        <div className="h-8 w-16 rounded bg-gray-700" />
      </div>
    </div>
  );
}

// ============================================
// Compact Single Alert (for header/navbar)
// ============================================

export interface CompactAlertIndicatorProps {
  className?: string;
  onClick?: () => void;
}

/**
 * Compact alert indicator for use in navigation or header.
 * Shows count badge when there are active alerts.
 */
export function CompactAlertIndicator({
  className,
  onClick,
}: CompactAlertIndicatorProps) {
  const { activeCount, criticalCount, hasActiveAlerts, isLoading } = useActiveAlerts();

  if (isLoading || !hasActiveAlerts) return null;

  const hasCritical = criticalCount > 0;

  return (
    <button
      onClick={onClick}
      className={clsx(
        'relative p-2 rounded-lg transition-colors',
        hasCritical
          ? 'text-red-400 hover:bg-red-500/10'
          : 'text-yellow-400 hover:bg-yellow-500/10',
        className
      )}
      title={`${activeCount} active safety alert${activeCount !== 1 ? 's' : ''}`}
    >
      <WarningIcon className="w-5 h-5" />
      <span
        className={clsx(
          'absolute -top-1 -right-1 flex items-center justify-center min-w-[18px] h-[18px] text-[10px] font-bold rounded-full',
          hasCritical ? 'bg-red-500' : 'bg-yellow-500',
          'text-white'
        )}
      >
        {activeCount}
      </span>
    </button>
  );
}

export default SafetyAlertBanner;
