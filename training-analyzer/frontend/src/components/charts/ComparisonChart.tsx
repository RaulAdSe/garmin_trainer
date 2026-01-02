'use client';

import { useMemo, useCallback, useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  Area,
  ComposedChart,
} from 'recharts';
import { useTranslations } from 'next-intl';
import type { NormalizedTimeSeries, ComparisonStats } from '@/types/comparison';

interface ComparisonChartProps {
  /**
   * Primary workout time series data.
   */
  primaryData: NormalizedTimeSeries;

  /**
   * Comparison workout time series data (optional).
   */
  comparisonData?: NormalizedTimeSeries | null;

  /**
   * Which metric to display.
   */
  metric: 'heart_rate' | 'pace' | 'power' | 'cadence' | 'elevation';

  /**
   * Label for the comparison workout.
   */
  comparisonLabel?: string;

  /**
   * Whether to show the difference area between lines.
   */
  showDifference?: boolean;

  /**
   * Whether to show comparison line.
   */
  showComparison?: boolean;

  /**
   * Height of the chart.
   */
  height?: number;

  /**
   * Comparison statistics for tooltip display.
   */
  stats?: ComparisonStats | null;

  /**
   * Optional class name.
   */
  className?: string;
}

/**
 * Chart component that overlays primary and comparison workout data.
 */
export function ComparisonChart({
  primaryData,
  comparisonData,
  metric,
  comparisonLabel = 'Comparison',
  showDifference = true,
  showComparison = true,
  height = 200,
  stats,
  className = '',
}: ComparisonChartProps) {
  const t = useTranslations('comparison');
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  // Metric configuration
  const metricConfig = useMemo(() => {
    const configs: Record<string, { color: string; unit: string; label: string; lowerIsBetter: boolean }> = {
      heart_rate: { color: '#ef4444', unit: 'bpm', label: t('metrics.heartRate'), lowerIsBetter: true },
      pace: { color: '#3b82f6', unit: '/km', label: t('metrics.pace'), lowerIsBetter: true },
      power: { color: '#a855f7', unit: 'W', label: t('metrics.power'), lowerIsBetter: false },
      cadence: { color: '#10b981', unit: 'spm', label: t('metrics.cadence'), lowerIsBetter: false },
      elevation: { color: '#6366f1', unit: 'm', label: t('metrics.elevation'), lowerIsBetter: false },
    };
    return configs[metric] || configs.heart_rate;
  }, [metric, t]);

  // Get the data array for the selected metric
  const getMetricData = useCallback(
    (series: NormalizedTimeSeries): (number | null)[] => {
      switch (metric) {
        case 'heart_rate':
          return series.heart_rate;
        case 'pace':
          return series.pace;
        case 'power':
          return series.power;
        case 'cadence':
          return series.cadence;
        case 'elevation':
          return series.elevation;
        default:
          return series.heart_rate;
      }
    },
    [metric]
  );

  // Combine data for the chart
  const chartData = useMemo(() => {
    const primaryValues = getMetricData(primaryData);
    const comparisonValues = comparisonData ? getMetricData(comparisonData) : null;

    return primaryData.timestamps.map((timestamp, index) => {
      const primaryValue = primaryValues[index];
      const comparisonValue = comparisonValues ? comparisonValues[index] : null;
      const difference =
        primaryValue !== null && comparisonValue !== null
          ? primaryValue - comparisonValue
          : null;

      return {
        timestamp,
        primary: primaryValue,
        comparison: comparisonValue,
        difference,
        // For difference highlighting
        positiveDiff: difference !== null && difference > 0 ? difference : null,
        negativeDiff: difference !== null && difference < 0 ? Math.abs(difference) : null,
      };
    });
  }, [primaryData, comparisonData, getMetricData]);

  // Calculate domain for Y axis
  const yDomain = useMemo(() => {
    const allValues = chartData.flatMap((d) => [d.primary, d.comparison]).filter((v) => v !== null) as number[];
    if (allValues.length === 0) return [0, 100];

    const min = Math.min(...allValues);
    const max = Math.max(...allValues);
    const padding = (max - min) * 0.1;

    return [Math.floor(min - padding), Math.ceil(max + padding)];
  }, [chartData]);

  // Format pace value (seconds to MM:SS)
  const formatPace = (seconds: number | null | undefined): string => {
    if (seconds === null || seconds === undefined) return '--';
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Format value for display
  const formatValue = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return '--';
    if (metric === 'pace') {
      return formatPace(value);
    }
    return value.toFixed(0);
  };

  // Custom tooltip
  const CustomTooltip = useCallback(
    ({ active, payload, label }: any) => {
      if (!active || !payload || !payload.length) return null;

      const data = payload[0]?.payload;
      if (!data) return null;

      return (
        <div className="bg-gray-800/95 border border-gray-700 rounded-lg px-3 py-2 shadow-xl text-sm">
          <div className="text-xs text-gray-400 mb-1.5">
            {Math.round(data.timestamp)}% {t('tooltip.ofWorkout')}
          </div>

          {/* Primary value */}
          <div className="flex items-center gap-2 mb-1">
            <span className="w-3 h-0.5 bg-teal-400 rounded" />
            <span className="text-gray-200">
              {formatValue(data.primary)} {metricConfig.unit}
            </span>
          </div>

          {/* Comparison value */}
          {data.comparison !== null && showComparison && (
            <div className="flex items-center gap-2 mb-1">
              <span
                className="w-3 h-0.5 bg-amber-400 rounded"
                style={{
                  backgroundImage:
                    'repeating-linear-gradient(to right, #fbbf24, #fbbf24 2px, transparent 2px, transparent 4px)',
                }}
              />
              <span className="text-gray-400">
                {formatValue(data.comparison)} {metricConfig.unit}
              </span>
            </div>
          )}

          {/* Difference */}
          {data.difference !== null && showComparison && (
            <div className="flex items-center gap-2 pt-1 border-t border-gray-700">
              {/* Determine if improvement (consider lowerIsBetter) */}
              {(() => {
                const isImprovement = metricConfig.lowerIsBetter
                  ? data.difference < 0
                  : data.difference > 0;

                return (
                  <span className={isImprovement ? 'text-green-400' : 'text-red-400'}>
                    {data.difference > 0 ? '+' : ''}
                    {formatValue(data.difference)} {metricConfig.unit}
                    {isImprovement ? ' (better)' : ' (worse)'}
                  </span>
                );
              })()}
            </div>
          )}
        </div>
      );
    },
    [metricConfig, showComparison, formatValue, t]
  );

  // Format X axis tick (percentage of workout)
  const formatXTick = (value: number): string => {
    return `${Math.round(value)}%`;
  };

  return (
    <div className={`w-full ${className}`}>
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart
          data={chartData}
          margin={{ top: 5, right: 5, left: -10, bottom: 0 }}
          onMouseMove={(e) => {
            if (e?.activeTooltipIndex !== undefined) {
              setHoveredIndex(e.activeTooltipIndex);
            }
          }}
          onMouseLeave={() => setHoveredIndex(null)}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />

          <XAxis
            dataKey="timestamp"
            stroke="#6b7280"
            fontSize={10}
            tickFormatter={formatXTick}
            tickCount={5}
          />

          <YAxis
            domain={yDomain}
            stroke="#6b7280"
            fontSize={10}
            tickFormatter={(value) => (metric === 'pace' ? formatPace(value) : value.toFixed(0))}
          />

          <Tooltip content={CustomTooltip} />

          {/* Difference area (if showing comparison) */}
          {showDifference && showComparison && comparisonData && (
            <>
              {/* Positive difference (primary > comparison) */}
              <Area
                type="monotone"
                dataKey="positiveDiff"
                fill={metricConfig.lowerIsBetter ? 'rgba(239, 68, 68, 0.1)' : 'rgba(34, 197, 94, 0.1)'}
                stroke="none"
                isAnimationActive={false}
              />
              {/* Negative difference (primary < comparison) */}
              <Area
                type="monotone"
                dataKey="negativeDiff"
                fill={metricConfig.lowerIsBetter ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)'}
                stroke="none"
                isAnimationActive={false}
              />
            </>
          )}

          {/* Comparison line (dashed) */}
          {showComparison && comparisonData && (
            <Line
              type="monotone"
              dataKey="comparison"
              stroke="#fbbf24"
              strokeWidth={1.5}
              strokeDasharray="5 5"
              dot={false}
              activeDot={{ r: 4, fill: '#fbbf24' }}
              isAnimationActive={false}
              connectNulls
            />
          )}

          {/* Primary line (solid) */}
          <Line
            type="monotone"
            dataKey="primary"
            stroke="#2dd4bf"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: '#2dd4bf' }}
            isAnimationActive={false}
            connectNulls
          />

          {/* Average reference lines */}
          {stats?.hr_avg_diff !== undefined && metric === 'heart_rate' && (
            <>
              {/* Primary average line */}
              {chartData.length > 0 && (
                <ReferenceLine
                  y={
                    chartData
                      .filter((d) => d.primary !== null)
                      .reduce((sum, d) => sum + (d.primary || 0), 0) /
                    chartData.filter((d) => d.primary !== null).length
                  }
                  stroke="#2dd4bf"
                  strokeDasharray="2 2"
                  strokeWidth={1}
                />
              )}
            </>
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

/**
 * Compact version of comparison chart for smaller displays.
 */
export function ComparisonChartCompact({
  primaryData,
  comparisonData,
  metric,
  showComparison = true,
  className = '',
}: Omit<ComparisonChartProps, 'height' | 'stats'>) {
  return (
    <ComparisonChart
      primaryData={primaryData}
      comparisonData={comparisonData}
      metric={metric}
      showComparison={showComparison}
      showDifference={false}
      height={120}
      className={className}
    />
  );
}

export default ComparisonChart;
