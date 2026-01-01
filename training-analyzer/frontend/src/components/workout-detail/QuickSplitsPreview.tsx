'use client';

import { useMemo } from 'react';
import type { SplitData } from '@/types/workout-detail';
import { BarChart3 } from 'lucide-react';

interface QuickSplitsPreviewProps {
  splits: SplitData[];
  isRunning: boolean;
  activeHoverIndex?: number | null;
  totalDataPoints?: number;
  onSplitHover?: (splitIndex: number | null) => void;
}

// Format pace in min:sec/km
function formatPace(secondsPerKm: number): string {
  const minutes = Math.floor(secondsPerKm / 60);
  const seconds = Math.floor(secondsPerKm % 60);
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

// Format speed in km/h
function formatSpeed(kmh: number): string {
  return `${kmh.toFixed(1)} km/h`;
}

export function QuickSplitsPreview({
  splits,
  isRunning,
  activeHoverIndex,
  totalDataPoints,
  onSplitHover,
}: QuickSplitsPreviewProps) {
  // Calculate cumulative distances for each split (to map hover index to split)
  // Route hover position corresponds to distance along route, not time
  const cumulativeDistances = useMemo(() => {
    let cumulative = 0;
    return splits.map(split => {
      cumulative += split.distance_m;
      return cumulative;
    });
  }, [splits]);

  // Calculate total distance
  const totalDistance = cumulativeDistances[cumulativeDistances.length - 1] || 0;

  // Determine which split is currently active based on hover index
  const activeSplitIndex = useMemo(() => {
    if (activeHoverIndex == null || !totalDataPoints || totalDistance === 0) {
      return null;
    }

    // Map hover index to distance (hover position is along the route)
    const currentDistance = (activeHoverIndex / totalDataPoints) * totalDistance;

    // Find which split this distance falls into
    for (let i = 0; i < cumulativeDistances.length; i++) {
      if (currentDistance <= cumulativeDistances[i]) {
        return i;
      }
    }
    return splits.length - 1;
  }, [activeHoverIndex, totalDataPoints, totalDistance, cumulativeDistances, splits.length]);

  // Calculate stats
  const { fastestIdx, stats } = useMemo(() => {
    if (splits.length === 0) {
      return { fastestIdx: -1, stats: null };
    }

    let fastest = 0;
    let minPace = Infinity;
    let maxPace = 0;
    let totalPace = 0;
    let count = 0;

    splits.forEach((s, i) => {
      const paceValue = isRunning ? s.avg_pace_sec_km : s.avg_speed_kmh;
      if (paceValue) {
        if (isRunning) {
          // For running, lower pace is better
          if (paceValue < minPace) {
            minPace = paceValue;
            fastest = i;
          }
          if (paceValue > maxPace) maxPace = paceValue;
        } else {
          // For cycling, higher speed is better
          if (paceValue > maxPace) {
            maxPace = paceValue;
            fastest = i;
          }
          if (paceValue < minPace) minPace = paceValue;
        }
        totalPace += paceValue;
        count++;
      }
    });

    return {
      fastestIdx: fastest,
      stats: count > 0 ? {
        best: isRunning ? minPace : maxPace,
        worst: isRunning ? maxPace : minPace,
        average: totalPace / count,
        minPace,
        maxPace,
      } : null,
    };
  }, [splits, isRunning]);

  if (splits.length === 0 || !stats) return null;

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-amber-500/20 flex items-center justify-center">
            <BarChart3 className="w-4 h-4 text-amber-400" />
          </div>
          <h3 className="text-sm font-medium text-gray-200">Split Times</h3>
        </div>
        <span className="text-xs text-gray-500">
          {splits.length} {isRunning ? 'km' : 'laps'}
        </span>
      </div>

      {/* Split bars - scrollable if many */}
      <div
        className="space-y-2 max-h-[280px] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent"
        onMouseLeave={() => onSplitHover?.(null)}
      >
        {splits.map((split, idx) => {
          const paceValue = isRunning ? split.avg_pace_sec_km : split.avg_speed_kmh;
          const isFastest = idx === fastestIdx;
          const isActive = idx === activeSplitIndex;

          // Calculate bar width - normalize to 60-100% range
          let barWidth = 80;
          if (paceValue && stats.minPace !== stats.maxPace) {
            if (isRunning) {
              // Running: lower pace = longer bar
              const normalized = 1 - (paceValue - stats.minPace) / (stats.maxPace - stats.minPace);
              barWidth = 60 + normalized * 40;
            } else {
              // Cycling: higher speed = longer bar
              const normalized = (paceValue - stats.minPace) / (stats.maxPace - stats.minPace);
              barWidth = 60 + normalized * 40;
            }
          }

          return (
            <div
              key={split.split_number}
              className={`flex items-center gap-3 py-1 px-1 -mx-1 rounded-md transition-all duration-150 ${
                isActive
                  ? 'bg-teal-500/20 ring-1 ring-teal-500/40'
                  : 'hover:bg-gray-800/30'
              }`}
              onMouseEnter={() => onSplitHover?.(idx)}
            >
              {/* Split number */}
              <span
                className={`w-5 text-xs text-right font-medium transition-colors ${
                  isActive ? 'text-teal-300' : isFastest ? 'text-green-400' : 'text-gray-500'
                }`}
              >
                {split.split_number}
              </span>

              {/* Bar container */}
              <div className={`flex-1 h-6 rounded-md overflow-hidden relative transition-all ${
                isActive ? 'bg-gray-700/50' : 'bg-gray-800/50'
              }`}>
                {/* Bar fill */}
                <div
                  className={`h-full rounded-md transition-all duration-300 ${
                    isActive
                      ? 'bg-gradient-to-r from-teal-500 to-teal-400'
                      : isFastest
                        ? 'bg-gradient-to-r from-green-600 to-green-500'
                        : 'bg-gradient-to-r from-teal-700 to-teal-600'
                  }`}
                  style={{ width: `${barWidth}%` }}
                />
                {/* HR overlay if available */}
                {split.avg_hr && (
                  <span className={`absolute right-2 top-1/2 -translate-y-1/2 text-[10px] transition-colors ${
                    isActive ? 'text-teal-300' : 'text-gray-400'
                  }`}>
                    {split.avg_hr} bpm
                  </span>
                )}
              </div>

              {/* Pace/Speed value */}
              <span
                className={`w-16 text-xs text-right font-medium transition-colors ${
                  isActive ? 'text-teal-300' : isFastest ? 'text-green-400' : 'text-gray-300'
                }`}
              >
                {paceValue
                  ? isRunning
                    ? formatPace(paceValue)
                    : formatSpeed(paceValue)
                  : '-'}
              </span>
            </div>
          );
        })}
      </div>

      {/* Summary footer */}
      <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-800">
        <div className="flex items-center gap-4 text-xs">
          <span className="text-gray-500">
            Avg:{' '}
            <span className="text-teal-400 font-medium">
              {isRunning ? formatPace(stats.average) : formatSpeed(stats.average)}
            </span>
          </span>
          <span className="text-gray-500">
            Best:{' '}
            <span className="text-green-400 font-medium">
              {isRunning ? formatPace(stats.best) : formatSpeed(stats.best)}
            </span>
          </span>
        </div>
        <span className="text-[10px] text-gray-600">
          {isRunning ? '/km' : 'km/h'}
        </span>
      </div>
    </div>
  );
}

export default QuickSplitsPreview;
