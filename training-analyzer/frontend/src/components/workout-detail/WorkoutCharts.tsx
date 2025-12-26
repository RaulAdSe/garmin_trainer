'use client';

import { useState, useCallback, useMemo } from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type {
  ActivityTimeSeries,
  HeartRatePoint,
  PaceSpeedPoint,
  ElevationPoint,
  SyncedHoverState,
} from '@/types/workout-detail';
import { formatChartTime, formatElapsedTime, downsampleData } from '@/lib/workout-utils';
import { formatPace } from '@/lib/utils';

// Chart theme colors
const COLORS = {
  grid: '#374151',
  text: '#9ca3af',
  heartRate: '#ef4444',
  pace: '#3b82f6',
  speed: '#22c55e',
  elevation: '#78716c',
  elevationFill: '#44403c',
  tooltipBg: '#1f2937',
  tooltipBorder: '#374151',
};

interface WorkoutChartsProps {
  timeSeries: ActivityTimeSeries;
  isRunning: boolean;
  maxHR?: number;
  className?: string;
  activeIndex?: number | null;
  onHoverIndexChange?: (index: number | null) => void;
}

export function WorkoutCharts({
  timeSeries,
  isRunning,
  maxHR = 185,
  className = '',
  activeIndex: externalActiveIndex,
  onHoverIndexChange,
}: WorkoutChartsProps) {
  const [internalHover, setInternalHover] = useState<SyncedHoverState>({
    activeIndex: null,
    activeLabel: null,
  });

  // Use external index if provided, otherwise internal
  const syncedHover: SyncedHoverState = {
    activeIndex: externalActiveIndex ?? internalHover.activeIndex,
    activeLabel: internalHover.activeLabel,
  };

  const handleMouseMove = useCallback((data: { activeTooltipIndex?: number; activeLabel?: string }) => {
    if (data.activeTooltipIndex !== undefined) {
      setInternalHover({
        activeIndex: data.activeTooltipIndex,
        activeLabel: data.activeLabel || null,
      });
      onHoverIndexChange?.(data.activeTooltipIndex);
    }
  }, [onHoverIndexChange]);

  const handleMouseLeave = useCallback(() => {
    setInternalHover({ activeIndex: null, activeLabel: null });
    onHoverIndexChange?.(null);
  }, [onHoverIndexChange]);

  // Check data availability
  const hasHRData = timeSeries.heart_rate.length > 0;
  const hasPaceData = timeSeries.pace_or_speed.length > 0;
  const hasElevationData = timeSeries.elevation.length > 0;

  if (!hasHRData && !hasPaceData && !hasElevationData) {
    return (
      <div className={`bg-gray-900 rounded-xl border border-gray-800 p-6 ${className}`}>
        <div className="text-center py-8">
          <svg className="w-12 h-12 text-gray-600 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <h3 className="text-sm font-medium text-gray-400">No Time-Series Data Available</h3>
          <p className="text-xs text-gray-500 mt-1">Detailed charts require activity stream data from Garmin</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Heart Rate Chart */}
      {hasHRData && (
        <HeartRateChart
          data={timeSeries.heart_rate}
          maxHR={maxHR}
          syncedHover={syncedHover}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        />
      )}

      {/* Pace/Speed Chart */}
      {hasPaceData && (
        <PaceSpeedChart
          data={timeSeries.pace_or_speed}
          isRunning={isRunning}
          syncedHover={syncedHover}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        />
      )}

      {/* Elevation Chart */}
      {hasElevationData && (
        <ElevationChart
          data={timeSeries.elevation}
          syncedHover={syncedHover}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        />
      )}
    </div>
  );
}

// Heart Rate Chart Component
interface HeartRateChartProps {
  data: HeartRatePoint[];
  maxHR: number;
  syncedHover: SyncedHoverState;
  onMouseMove: (data: { activeTooltipIndex?: number; activeLabel?: string }) => void;
  onMouseLeave: () => void;
}

function HeartRateChart({ data, maxHR, syncedHover, onMouseMove, onMouseLeave }: HeartRateChartProps) {
  const chartData = useMemo(() => {
    const downsampled = downsampleData(data, 400);
    return downsampled.map(point => ({
      timestamp: point.timestamp,
      hr: point.hr,
    }));
  }, [data]);

  const { minHR, maxHRValue } = useMemo(() => {
    const hrs = chartData.map(d => d.hr).filter(hr => hr > 0);
    return {
      minHR: Math.max(40, Math.min(...hrs) - 10),
      maxHRValue: Math.max(...hrs) + 10,
    };
  }, [chartData]);

  // HR Zone lines
  const hrZones = [
    { pct: 60, color: '#22c55e' },
    { pct: 70, color: '#3b82f6' },
    { pct: 80, color: '#eab308' },
    { pct: 90, color: '#f97316' },
  ];

  // Get synced position data
  const syncedData = useMemo(() => {
    if (syncedHover.activeIndex === null || syncedHover.activeIndex >= chartData.length) return null;
    const point = chartData[syncedHover.activeIndex];
    return { timestamp: point.timestamp, value: point.hr };
  }, [syncedHover.activeIndex, chartData]);

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
          <h3 className="text-sm font-medium text-gray-200">Heart Rate</h3>
        </div>
        {/* Synced value display */}
        {syncedData && (
          <div className="text-sm text-gray-300">
            <span className="text-gray-500">{formatElapsedTime(syncedData.timestamp)}</span>
            <span className="mx-2 text-gray-600">|</span>
            <span className="text-red-400 font-medium">{syncedData.value} bpm</span>
          </div>
        )}
      </div>
      <div className="h-40 sm:h-48">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            onMouseMove={onMouseMove}
            onMouseLeave={onMouseLeave}
            margin={{ top: 5, right: 5, left: 0, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} vertical={false} />
            <XAxis
              dataKey="timestamp"
              stroke={COLORS.text}
              fontSize={11}
              tickLine={false}
              axisLine={false}
              tickFormatter={formatChartTime}
              minTickGap={50}
            />
            <YAxis
              stroke={COLORS.text}
              fontSize={11}
              tickLine={false}
              axisLine={false}
              domain={[minHR, maxHRValue]}
              width={35}
              tickFormatter={(val) => `${val}`}
            />
            <Tooltip
              content={<CustomTooltip label="HR" unit=" bpm" />}
              cursor={{ stroke: '#6b7280', strokeDasharray: '3 3' }}
            />
            {/* HR Zone reference lines */}
            {hrZones.map(zone => (
              <ReferenceLine
                key={zone.pct}
                y={Math.round(maxHR * zone.pct / 100)}
                stroke={zone.color}
                strokeDasharray="5 5"
                strokeOpacity={0.4}
              />
            ))}
            {/* Synced vertical reference line */}
            {syncedData && (
              <ReferenceLine
                x={syncedData.timestamp}
                stroke="#fbbf24"
                strokeDasharray="4 4"
                strokeWidth={2}
              />
            )}
            <Line
              type="monotone"
              dataKey="hr"
              stroke={COLORS.heartRate}
              strokeWidth={1.5}
              dot={false}
              activeDot={{ r: 4, fill: COLORS.heartRate, stroke: '#fff', strokeWidth: 2 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// Pace/Speed Chart Component
interface PaceSpeedChartProps {
  data: PaceSpeedPoint[];
  isRunning: boolean;
  syncedHover: SyncedHoverState;
  onMouseMove: (data: { activeTooltipIndex?: number; activeLabel?: string }) => void;
  onMouseLeave: () => void;
}

function PaceSpeedChart({ data, isRunning, syncedHover, onMouseMove, onMouseLeave }: PaceSpeedChartProps) {
  const chartData = useMemo(() => {
    const downsampled = downsampleData(data, 400);
    return downsampled.map(point => ({
      timestamp: point.timestamp,
      value: point.value,
    }));
  }, [data]);

  const { minValue, maxValue } = useMemo(() => {
    const values = chartData.map(d => d.value).filter(v => v > 0);
    if (values.length === 0) return { minValue: 0, maxValue: 100 };

    if (isRunning) {
      // Pace: lower is better, show range for reasonable paces
      return {
        minValue: Math.max(180, Math.min(...values) - 30), // 3:00/km min
        maxValue: Math.min(900, Math.max(...values) + 30), // 15:00/km max
      };
    } else {
      // Speed: higher is better
      return {
        minValue: Math.max(0, Math.min(...values) - 5),
        maxValue: Math.max(...values) + 5,
      };
    }
  }, [chartData, isRunning]);

  const formatYAxis = (value: number) => {
    if (isRunning) {
      return formatPace(value);
    }
    return `${value.toFixed(0)}`;
  };

  const chartColor = isRunning ? COLORS.pace : COLORS.speed;
  const title = isRunning ? 'Pace' : 'Speed';
  const unit = isRunning ? ' /km' : ' km/h';
  const iconColor = isRunning ? 'text-blue-500' : 'text-green-500';

  // Get synced position data
  const syncedData = useMemo(() => {
    if (syncedHover.activeIndex === null || syncedHover.activeIndex >= chartData.length) return null;
    const point = chartData[syncedHover.activeIndex];
    return { timestamp: point.timestamp, value: point.value };
  }, [syncedHover.activeIndex, chartData]);

  const formatValue = isRunning ? (v: number) => formatPace(v) : (v: number) => v.toFixed(1);

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <svg className={`w-5 h-5 ${iconColor}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <h3 className="text-sm font-medium text-gray-200">{title}</h3>
        </div>
        {/* Synced value display */}
        {syncedData && (
          <div className="text-sm text-gray-300">
            <span className="text-gray-500">{formatElapsedTime(syncedData.timestamp)}</span>
            <span className="mx-2 text-gray-600">|</span>
            <span className={`${isRunning ? 'text-blue-400' : 'text-green-400'} font-medium`}>
              {formatValue(syncedData.value)}{unit}
            </span>
          </div>
        )}
      </div>
      <div className="h-40 sm:h-48">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            onMouseMove={onMouseMove}
            onMouseLeave={onMouseLeave}
            margin={{ top: 5, right: 5, left: 0, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} vertical={false} />
            <XAxis
              dataKey="timestamp"
              stroke={COLORS.text}
              fontSize={11}
              tickLine={false}
              axisLine={false}
              tickFormatter={formatChartTime}
              minTickGap={50}
            />
            <YAxis
              stroke={COLORS.text}
              fontSize={11}
              tickLine={false}
              axisLine={false}
              domain={[minValue, maxValue]}
              width={45}
              tickFormatter={formatYAxis}
              reversed={isRunning} // Invert Y for pace (lower is faster)
            />
            <Tooltip
              content={
                <CustomTooltip
                  label={title}
                  unit={unit}
                  valueFormatter={formatValue}
                />
              }
              cursor={{ stroke: '#6b7280', strokeDasharray: '3 3' }}
            />
            {/* Synced vertical reference line */}
            {syncedData && (
              <ReferenceLine
                x={syncedData.timestamp}
                stroke="#fbbf24"
                strokeDasharray="4 4"
                strokeWidth={2}
              />
            )}
            <Line
              type="monotone"
              dataKey="value"
              stroke={chartColor}
              strokeWidth={1.5}
              dot={false}
              activeDot={{ r: 4, fill: chartColor, stroke: '#fff', strokeWidth: 2 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// Elevation Chart Component
interface ElevationChartProps {
  data: ElevationPoint[];
  syncedHover: SyncedHoverState;
  onMouseMove: (data: { activeTooltipIndex?: number; activeLabel?: string }) => void;
  onMouseLeave: () => void;
}

function ElevationChart({ data, syncedHover, onMouseMove, onMouseLeave }: ElevationChartProps) {
  const chartData = useMemo(() => {
    const downsampled = downsampleData(data, 400);
    return downsampled.map(point => ({
      timestamp: point.timestamp,
      elevation: point.elevation,
    }));
  }, [data]);

  const { minElev, maxElev, totalGain, totalLoss } = useMemo(() => {
    const elevations = chartData.map(d => d.elevation);
    const min = Math.min(...elevations);
    const max = Math.max(...elevations);

    // Calculate total gain/loss
    let gain = 0;
    let loss = 0;
    for (let i = 1; i < chartData.length; i++) {
      const diff = chartData[i].elevation - chartData[i - 1].elevation;
      if (diff > 0) gain += diff;
      else loss += Math.abs(diff);
    }

    const padding = (max - min) * 0.1 || 10;
    return {
      minElev: Math.floor(min - padding),
      maxElev: Math.ceil(max + padding),
      totalGain: Math.round(gain),
      totalLoss: Math.round(loss),
    };
  }, [chartData]);

  // Get synced position data
  const syncedData = useMemo(() => {
    if (syncedHover.activeIndex === null || syncedHover.activeIndex >= chartData.length) return null;
    const point = chartData[syncedHover.activeIndex];
    return { timestamp: point.timestamp, value: point.elevation };
  }, [syncedHover.activeIndex, chartData]);

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-stone-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
          <h3 className="text-sm font-medium text-gray-200">Elevation</h3>
          {/* Synced value display */}
          {syncedData && (
            <span className="ml-2 text-sm text-gray-300">
              <span className="text-gray-500">{formatElapsedTime(syncedData.timestamp)}</span>
              <span className="mx-2 text-gray-600">|</span>
              <span className="text-stone-400 font-medium">{syncedData.value.toFixed(0)}m</span>
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-400">
          <span className="flex items-center gap-1">
            <svg className="w-3 h-3 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
            </svg>
            {totalGain}m
          </span>
          <span className="flex items-center gap-1">
            <svg className="w-3 h-3 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
            {totalLoss}m
          </span>
        </div>
      </div>
      <div className="h-28 sm:h-36">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            onMouseMove={onMouseMove}
            onMouseLeave={onMouseLeave}
            margin={{ top: 5, right: 5, left: 0, bottom: 5 }}
          >
            <defs>
              <linearGradient id="elevationGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={COLORS.elevation} stopOpacity={0.6} />
                <stop offset="100%" stopColor={COLORS.elevationFill} stopOpacity={0.1} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} vertical={false} />
            <XAxis
              dataKey="timestamp"
              stroke={COLORS.text}
              fontSize={11}
              tickLine={false}
              axisLine={false}
              tickFormatter={formatChartTime}
              minTickGap={50}
            />
            <YAxis
              stroke={COLORS.text}
              fontSize={11}
              tickLine={false}
              axisLine={false}
              domain={[minElev, maxElev]}
              width={40}
              tickFormatter={(val) => `${val}m`}
            />
            <Tooltip
              content={<CustomTooltip label="Elevation" unit="m" valueFormatter={(v: number) => v.toFixed(0)} />}
              cursor={{ stroke: '#6b7280', strokeDasharray: '3 3' }}
            />
            {/* Synced vertical reference line */}
            {syncedData && (
              <ReferenceLine
                x={syncedData.timestamp}
                stroke="#fbbf24"
                strokeDasharray="4 4"
                strokeWidth={2}
              />
            )}
            <Area
              type="monotone"
              dataKey="elevation"
              stroke={COLORS.elevation}
              strokeWidth={1.5}
              fill="url(#elevationGradient)"
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// Custom Tooltip Component
interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: Record<string, unknown>; value: number }>;
  label: string;
  unit: string;
  valueFormatter?: (value: number) => string;
}

function CustomTooltip({ active, payload, label, unit, valueFormatter = (v) => v.toString() }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const data = payload[0].payload;
  const timestamp = data.timestamp as number;
  const value = payload[0].value;

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 shadow-xl">
      <div className="text-xs text-gray-400 mb-1">{formatElapsedTime(timestamp)}</div>
      <div className="text-sm font-medium text-gray-100">
        {label}: <span className="text-teal-400">{valueFormatter(value)}{unit}</span>
      </div>
    </div>
  );
}

export default WorkoutCharts;
