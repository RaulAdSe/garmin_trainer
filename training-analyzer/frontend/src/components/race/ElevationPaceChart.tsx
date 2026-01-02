'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Card } from '@/components/ui';
import type { PacingPlan } from '@/lib/types';

interface ElevationPaceChartProps {
  plan: PacingPlan;
}

interface ChartDataPoint {
  distance: number;
  elevation: number;
  pace: number;
  paceFormatted: string;
}

export default function ElevationPaceChart({ plan }: ElevationPaceChartProps) {
  const t = useTranslations('racePacing.chart');

  // Prepare chart data
  const chartData: ChartDataPoint[] = React.useMemo(() => {
    if (!plan.course_profile || plan.course_profile.elevation_points.length === 0) {
      return [];
    }

    const elevationPoints = plan.course_profile.elevation_points;
    const splits = plan.splits;

    // Map elevation points to chart data
    return elevationPoints.map((point, index) => {
      // Find the corresponding split for this distance
      const splitIndex = Math.min(
        Math.floor(point.distance_km),
        splits.length - 1
      );
      const split = splits[splitIndex];

      return {
        distance: point.distance_km,
        elevation: point.elevation_m,
        pace: split?.target_pace_sec_km || plan.base_pace_sec_km,
        paceFormatted: split?.target_pace_formatted || plan.base_pace_formatted,
      };
    });
  }, [plan]);

  if (chartData.length === 0) {
    return null;
  }

  const minElevation = Math.min(...chartData.map((d) => d.elevation));
  const maxElevation = Math.max(...chartData.map((d) => d.elevation));
  const elevationRange = maxElevation - minElevation;

  const formatPace = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const elevationData = payload.find((p: any) => p.dataKey === 'elevation');
      const paceData = payload.find((p: any) => p.dataKey === 'pace');

      return (
        <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 shadow-lg">
          <p className="text-gray-300 text-sm mb-2">
            {t('distance')}: {label.toFixed(1)} km
          </p>
          {elevationData && (
            <p className="text-blue-400 text-sm">
              {t('elevation')}: {Math.round(elevationData.value)}m
            </p>
          )}
          {paceData && (
            <p className="text-orange-400 text-sm">
              {t('pace')}: {formatPace(paceData.value)}/km
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold text-white mb-2">{t('title')}</h3>
      <p className="text-sm text-gray-400 mb-4">{t('subtitle')}</p>

      {/* Elevation Stats */}
      <div className="flex gap-4 mb-4 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-gray-400">{t('totalClimb')}:</span>
          <span className="text-white font-medium">
            {Math.round(plan.course_profile?.total_elevation_gain_m || 0)}m
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-gray-400">{t('totalDescent')}:</span>
          <span className="text-white font-medium">
            {Math.round(plan.course_profile?.total_elevation_loss_m || 0)}m
          </span>
        </div>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={chartData}
            margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id="elevationGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="distance"
              stroke="#9CA3AF"
              tick={{ fill: '#9CA3AF', fontSize: 12 }}
              tickFormatter={(value) => `${value}km`}
            />
            <YAxis
              yAxisId="elevation"
              orientation="left"
              stroke="#3B82F6"
              tick={{ fill: '#3B82F6', fontSize: 12 }}
              domain={[
                Math.floor(minElevation - elevationRange * 0.1),
                Math.ceil(maxElevation + elevationRange * 0.1),
              ]}
              tickFormatter={(value) => `${value}m`}
            />
            <YAxis
              yAxisId="pace"
              orientation="right"
              stroke="#F97316"
              tick={{ fill: '#F97316', fontSize: 12 }}
              domain={['auto', 'auto']}
              tickFormatter={formatPace}
              reversed
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ paddingTop: '10px' }}
              formatter={(value) => (
                <span className="text-gray-300 text-sm">
                  {value === 'elevation' ? t('elevation') : t('targetPace')}
                </span>
              )}
            />
            <Area
              yAxisId="elevation"
              type="monotone"
              dataKey="elevation"
              stroke="#3B82F6"
              fill="url(#elevationGradient)"
              strokeWidth={2}
            />
            <Line
              yAxisId="pace"
              type="stepAfter"
              dataKey="pace"
              stroke="#F97316"
              strokeWidth={2}
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Pace adjustment note */}
      <p className="text-xs text-gray-500 mt-4">
        {t('paceAdjustmentNote')}
      </p>
    </Card>
  );
}
