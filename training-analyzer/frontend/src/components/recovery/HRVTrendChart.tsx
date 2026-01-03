'use client';

import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui/Card';
import type { HRVTrendResponse } from '@/lib/types';

interface HRVTrendChartProps {
  data?: HRVTrendResponse | null;
}

export function HRVTrendChart({ data }: HRVTrendChartProps) {
  const t = useTranslations('recovery');

  if (!data?.success || !data.data) {
    return (
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">HRV Trend</h3>
        <div className="text-center py-8">
          <p className="text-gray-400">{data?.error || t('noHRVData')}</p>
        </div>
      </Card>
    );
  }

  const hrvTrend = data.data;

  // Get trend direction color
  const getTrendColor = (direction: string) => {
    switch (direction) {
      case 'improving':
        return 'text-green-400';
      case 'declining':
        return 'text-red-400';
      default:
        return 'text-blue-400';
    }
  };

  const formatTrendDirection = (direction: string) => {
    return direction.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  };

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-100">HRV Trend</h3>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">Trend:</span>
          <span className={`text-sm font-medium ${getTrendColor(hrvTrend.trendDirection)}`}>
            {formatTrendDirection(hrvTrend.trendDirection)}
            {hrvTrend.trendPercentage != null && (
              <span className="ml-1">({hrvTrend.trendPercentage > 0 ? '+' : ''}{hrvTrend.trendPercentage.toFixed(1)}%)</span>
            )}
          </span>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-3 bg-gray-800/50 rounded-lg">
          <p className="text-xs text-gray-500 mb-1">Current HRV</p>
          <p className="text-lg font-semibold text-gray-200">
            {hrvTrend.currentRmssd?.toFixed(0) || '--'} ms
          </p>
        </div>
        <div className="p-3 bg-gray-800/50 rounded-lg">
          <p className="text-xs text-gray-500 mb-1">7-Day Avg</p>
          <p className="text-lg font-semibold text-gray-200">
            {hrvTrend.rollingAverage7d?.toFixed(0) || '--'} ms
          </p>
        </div>
        <div className="p-3 bg-gray-800/50 rounded-lg">
          <p className="text-xs text-gray-500 mb-1">30-Day Avg</p>
          <p className="text-lg font-semibold text-gray-200">
            {hrvTrend.rollingAverage30d?.toFixed(0) || '--'} ms
          </p>
        </div>
        <div className="p-3 bg-gray-800/50 rounded-lg">
          <p className="text-xs text-gray-500 mb-1">CV (7d)</p>
          <p className="text-lg font-semibold text-gray-200">
            {hrvTrend.cv7d?.toFixed(1) || '--'}%
          </p>
        </div>
      </div>

      {/* Baseline Comparison */}
      {hrvTrend.baselineRmssd != null && hrvTrend.relativeToBaseline != null && (
        <div className="mt-4 p-3 bg-gray-800/50 rounded-lg">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Relative to Baseline ({hrvTrend.baselineRmssd.toFixed(0)} ms)</span>
            <span className={`text-sm font-medium ${hrvTrend.relativeToBaseline >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {hrvTrend.relativeToBaseline >= 0 ? '+' : ''}{hrvTrend.relativeToBaseline.toFixed(1)}%
            </span>
          </div>
        </div>
      )}

      {/* Interpretation */}
      {hrvTrend.interpretation && (
        <div className="mt-4 p-3 bg-teal-500/10 border border-teal-500/30 rounded-lg">
          <p className="text-sm text-teal-300">{hrvTrend.interpretation}</p>
        </div>
      )}

      {/* Data Quality */}
      <div className="mt-4 pt-4 border-t border-gray-800">
        <p className="text-xs text-gray-500">
          Based on {hrvTrend.dataPoints7d} readings (7d) / {hrvTrend.dataPoints30d} readings (30d)
        </p>
      </div>
    </Card>
  );
}
