'use client';

import { useMemo } from 'react';
import { useTranslations } from 'next-intl';
import type { ComparisonStats, ComparisonLegendItem } from '@/types/comparison';

interface ComparisonLegendProps {
  /**
   * Name/label for the primary (current) workout.
   */
  primaryLabel: string;

  /**
   * Name/label for the comparison workout.
   */
  comparisonLabel: string;

  /**
   * Comparison statistics to display.
   */
  stats?: ComparisonStats | null;

  /**
   * Which metric is currently being displayed.
   */
  activeMetric?: 'heart_rate' | 'pace' | 'power' | 'cadence' | 'elevation';

  /**
   * Callback when a legend item is clicked (for toggling visibility).
   */
  onItemClick?: (id: 'primary' | 'comparison') => void;

  /**
   * Whether the comparison line is visible.
   */
  comparisonVisible?: boolean;

  /**
   * Optional class name for styling.
   */
  className?: string;
}

/**
 * Legend component for comparison charts.
 * Shows primary vs comparison workout indicators with optional stats.
 */
export function ComparisonLegend({
  primaryLabel,
  comparisonLabel,
  stats,
  activeMetric = 'heart_rate',
  onItemClick,
  comparisonVisible = true,
  className = '',
}: ComparisonLegendProps) {
  const t = useTranslations('comparison');

  // Calculate display values based on active metric
  const metricInfo = useMemo(() => {
    if (!stats) return null;

    switch (activeMetric) {
      case 'heart_rate':
        return {
          diff: stats.hr_avg_diff,
          improvement: stats.improvement_metrics?.hr_efficiency,
          unit: 'bpm',
          lowerIsBetter: true, // Lower HR at same pace = better efficiency
        };
      case 'pace':
        return {
          diff: stats.pace_avg_diff,
          improvement: stats.improvement_metrics?.pace,
          unit: 'sec/km',
          lowerIsBetter: true, // Lower pace = faster
        };
      case 'power':
        return {
          diff: stats.power_avg_diff,
          improvement: stats.improvement_metrics?.power,
          unit: 'W',
          lowerIsBetter: false, // Higher power = more output
        };
      default:
        return null;
    }
  }, [stats, activeMetric]);

  // Format difference value for display
  const formatDiff = (value: number | undefined | null, unit: string): string => {
    if (value === undefined || value === null) return '--';
    const sign = value > 0 ? '+' : '';
    return `${sign}${value.toFixed(1)} ${unit}`;
  };

  // Format improvement percentage
  const formatImprovement = (value: number | undefined | null): string => {
    if (value === undefined || value === null) return '';
    const sign = value > 0 ? '+' : '';
    return `${sign}${value.toFixed(1)}%`;
  };

  // Determine if the current workout is better
  const isBetter = useMemo(() => {
    if (!metricInfo || metricInfo.diff === undefined || metricInfo.diff === null) return null;

    if (metricInfo.lowerIsBetter) {
      return metricInfo.diff < 0;
    }
    return metricInfo.diff > 0;
  }, [metricInfo]);

  return (
    <div className={`flex flex-wrap items-center gap-4 text-sm ${className}`}>
      {/* Primary workout legend item */}
      <button
        type="button"
        onClick={() => onItemClick?.('primary')}
        className="flex items-center gap-2 hover:opacity-80 transition-opacity"
      >
        <span className="relative flex items-center">
          <span className="w-6 h-0.5 bg-teal-400 rounded" />
        </span>
        <span className="text-gray-200 font-medium truncate max-w-[120px]" title={primaryLabel}>
          {t('legend.current')}
        </span>
      </button>

      {/* Comparison workout legend item */}
      <button
        type="button"
        onClick={() => onItemClick?.('comparison')}
        className={`flex items-center gap-2 transition-opacity ${
          comparisonVisible ? 'opacity-100 hover:opacity-80' : 'opacity-50'
        }`}
      >
        <span className="relative flex items-center">
          <span
            className="w-6 h-0.5 bg-amber-400 rounded"
            style={{
              backgroundImage: 'repeating-linear-gradient(to right, #fbbf24, #fbbf24 4px, transparent 4px, transparent 8px)',
            }}
          />
        </span>
        <span className="text-gray-300 truncate max-w-[120px]" title={comparisonLabel}>
          {comparisonLabel}
        </span>
      </button>

      {/* Stats display */}
      {metricInfo && (
        <div className="flex items-center gap-2 ml-auto">
          {/* Difference badge */}
          {metricInfo.diff !== undefined && metricInfo.diff !== null && (
            <span
              className={`px-2 py-0.5 rounded text-xs font-medium ${
                isBetter === null
                  ? 'bg-gray-700 text-gray-300'
                  : isBetter
                  ? 'bg-green-900/50 text-green-400'
                  : 'bg-red-900/50 text-red-400'
              }`}
            >
              {formatDiff(metricInfo.diff, metricInfo.unit)}
            </span>
          )}

          {/* Improvement indicator */}
          {metricInfo.improvement !== undefined && metricInfo.improvement !== null && (
            <span className="text-xs text-gray-400">
              {isBetter && <span className="text-green-400 mr-1">&#8593;</span>}
              {!isBetter && isBetter !== null && <span className="text-red-400 mr-1">&#8595;</span>}
              {formatImprovement(metricInfo.improvement)}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Minimal legend for smaller chart displays.
 */
export function ComparisonLegendMinimal({
  primaryLabel = 'Current',
  comparisonLabel = 'Comparison',
  className = '',
}: Pick<ComparisonLegendProps, 'primaryLabel' | 'comparisonLabel' | 'className'>) {
  return (
    <div className={`flex items-center gap-3 text-xs ${className}`}>
      <div className="flex items-center gap-1.5">
        <span className="w-4 h-0.5 bg-teal-400 rounded" />
        <span className="text-gray-400">{primaryLabel}</span>
      </div>
      <div className="flex items-center gap-1.5">
        <span
          className="w-4 h-0.5 bg-amber-400 rounded"
          style={{
            backgroundImage: 'repeating-linear-gradient(to right, #fbbf24, #fbbf24 2px, transparent 2px, transparent 4px)',
          }}
        />
        <span className="text-gray-400">{comparisonLabel}</span>
      </div>
    </div>
  );
}

export default ComparisonLegend;
