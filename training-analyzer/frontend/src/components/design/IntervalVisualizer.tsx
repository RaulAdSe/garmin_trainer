'use client';

import { useMemo } from 'react';
import type { WorkoutInterval } from '@/lib/types';
import { INTERVAL_TYPE_COLORS, INTERVAL_TYPE_LABELS } from '@/lib/types';

interface IntervalVisualizerProps {
  intervals: WorkoutInterval[];
  className?: string;
  showLabels?: boolean;
  showLegend?: boolean;
  height?: number;
  onIntervalClick?: (interval: WorkoutInterval, index: number) => void;
}

// Format duration for display
function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hours > 0) {
    return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Format pace for display
function formatPace(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Calculate intensity level (0-1) based on interval type
function getIntensityLevel(interval: WorkoutInterval): number {
  const intensityMap: Record<string, number> = {
    rest: 0.1,
    recovery: 0.3,
    warmup: 0.4,
    cooldown: 0.4,
    work: 0.8,
  };
  return intensityMap[interval.type] || 0.5;
}

export function IntervalVisualizer({
  intervals,
  className = '',
  showLabels = true,
  showLegend = true,
  height = 120,
  onIntervalClick,
}: IntervalVisualizerProps) {
  const totalDuration = useMemo(
    () => intervals.reduce((sum, interval) => sum + interval.duration, 0),
    [intervals]
  );

  const barData = useMemo(() => {
    if (totalDuration === 0) return [];

    let cumulativePercent = 0;
    return intervals.map((interval, index) => {
      const widthPercent = (interval.duration / totalDuration) * 100;
      const startPercent = cumulativePercent;
      cumulativePercent += widthPercent;

      return {
        interval,
        index,
        widthPercent,
        startPercent,
        color: INTERVAL_TYPE_COLORS[interval.type],
        intensity: getIntensityLevel(interval),
      };
    });
  }, [intervals, totalDuration]);

  // Calculate time markers
  const timeMarkers = useMemo(() => {
    if (totalDuration === 0) return [];

    const markers: { time: number; percent: number }[] = [];
    const intervalSeconds = totalDuration <= 1800 ? 300 : 600; // 5 or 10 minute intervals

    for (let t = intervalSeconds; t < totalDuration; t += intervalSeconds) {
      markers.push({
        time: t,
        percent: (t / totalDuration) * 100,
      });
    }

    return markers;
  }, [totalDuration]);

  // Get unique interval types for legend
  const uniqueTypes = useMemo(() => {
    const types = new Set(intervals.map((i) => i.type));
    return Array.from(types);
  }, [intervals]);

  if (intervals.length === 0) {
    return (
      <div
        className={`flex items-center justify-center text-gray-400 dark:text-gray-500 border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-lg ${className}`}
        style={{ height }}
      >
        No intervals to visualize
      </div>
    );
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Main visualization */}
      <div className="relative" style={{ height }}>
        {/* Background grid */}
        <div className="absolute inset-0 flex">
          {timeMarkers.map((marker, idx) => (
            <div
              key={idx}
              className="absolute h-full border-l border-gray-200 dark:border-gray-700 border-dashed"
              style={{ left: `${marker.percent}%` }}
            />
          ))}
        </div>

        {/* Interval bars */}
        <div className="absolute inset-0 flex">
          {barData.map(({ interval, index, widthPercent, color, intensity }) => (
            <div
              key={interval.id}
              className={`relative h-full transition-all group ${
                onIntervalClick ? 'cursor-pointer hover:opacity-90' : ''
              }`}
              style={{
                width: `${widthPercent}%`,
                minWidth: widthPercent > 0 ? '2px' : 0,
              }}
              onClick={() => onIntervalClick?.(interval, index)}
            >
              {/* Bar with intensity-based height */}
              <div
                className="absolute bottom-0 left-0 right-0 rounded-t-sm transition-all"
                style={{
                  height: `${intensity * 100}%`,
                  backgroundColor: color,
                  marginLeft: '1px',
                  marginRight: '1px',
                }}
              />

              {/* Hover tooltip */}
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity z-10 pointer-events-none">
                <div className="bg-gray-900 text-white text-xs rounded-lg px-3 py-2 whitespace-nowrap shadow-lg">
                  <div className="font-medium">
                    {interval.name || INTERVAL_TYPE_LABELS[interval.type]}
                  </div>
                  <div className="text-gray-300">
                    {formatDuration(interval.duration)}
                  </div>
                  {interval.paceTarget && (
                    <div className="text-gray-300">
                      Pace: {formatPace(interval.paceTarget.min)} -{' '}
                      {formatPace(interval.paceTarget.max)}{' '}
                      {interval.paceTarget.unit}
                    </div>
                  )}
                  {interval.hrTarget && (
                    <div className="text-gray-300">
                      HR: {interval.hrTarget.min} - {interval.hrTarget.max} bpm
                    </div>
                  )}
                </div>
                {/* Tooltip arrow */}
                <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
              </div>
            </div>
          ))}
        </div>

        {/* Time markers labels */}
        <div className="absolute inset-x-0 bottom-0 h-6">
          {timeMarkers.map((marker, idx) => (
            <div
              key={idx}
              className="absolute text-xs text-gray-400 dark:text-gray-500"
              style={{
                left: `${marker.percent}%`,
                transform: 'translateX(-50%)',
              }}
            >
              {formatDuration(marker.time)}
            </div>
          ))}
        </div>
      </div>

      {/* Labels below bars */}
      {showLabels && (
        <div className="flex">
          {barData.map(({ interval, widthPercent }) => (
            <div
              key={interval.id}
              className="overflow-hidden text-center"
              style={{
                width: `${widthPercent}%`,
                minWidth: widthPercent > 0 ? '2px' : 0,
              }}
            >
              {widthPercent > 8 && (
                <div className="text-xs text-gray-500 dark:text-gray-400 truncate px-1">
                  {interval.name || INTERVAL_TYPE_LABELS[interval.type]}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Legend */}
      {showLegend && uniqueTypes.length > 0 && (
        <div className="flex flex-wrap gap-4 pt-2">
          {uniqueTypes.map((type) => (
            <div key={type} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-sm"
                style={{ backgroundColor: INTERVAL_TYPE_COLORS[type] }}
              />
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {INTERVAL_TYPE_LABELS[type]}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Summary stats */}
      <div className="flex items-center gap-6 text-sm text-gray-500 dark:text-gray-400 pt-2 border-t border-gray-200 dark:border-gray-700">
        <div>
          <span className="font-medium text-gray-900 dark:text-white">
            {intervals.length}
          </span>{' '}
          intervals
        </div>
        <div>
          <span className="font-medium text-gray-900 dark:text-white">
            {formatDuration(totalDuration)}
          </span>{' '}
          total
        </div>
        {intervals.some((i) => i.type === 'work') && (
          <div>
            <span className="font-medium text-gray-900 dark:text-white">
              {formatDuration(
                intervals
                  .filter((i) => i.type === 'work')
                  .reduce((sum, i) => sum + i.duration, 0)
              )}
            </span>{' '}
            work time
          </div>
        )}
      </div>
    </div>
  );
}

// Compact version for cards/previews
export function IntervalVisualizerCompact({
  intervals,
  className = '',
  height = 24,
}: {
  intervals: WorkoutInterval[];
  className?: string;
  height?: number;
}) {
  const totalDuration = intervals.reduce((sum, i) => sum + i.duration, 0);

  if (intervals.length === 0 || totalDuration === 0) {
    return (
      <div
        className={`bg-gray-100 dark:bg-gray-800 rounded ${className}`}
        style={{ height }}
      />
    );
  }

  return (
    <div
      className={`flex rounded overflow-hidden ${className}`}
      style={{ height }}
    >
      {intervals.map((interval) => (
        <div
          key={interval.id}
          style={{
            width: `${(interval.duration / totalDuration) * 100}%`,
            backgroundColor: INTERVAL_TYPE_COLORS[interval.type],
            minWidth: '2px',
          }}
        />
      ))}
    </div>
  );
}

export default IntervalVisualizer;
