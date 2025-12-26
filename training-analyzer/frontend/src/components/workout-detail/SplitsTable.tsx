'use client';

import { useMemo } from 'react';
import type { SplitData } from '@/types/workout-detail';
import { formatPace, formatDuration } from '@/lib/utils';

interface SplitsTableProps {
  splits: SplitData[];
  isRunning: boolean;
  className?: string;
}

export function SplitsTable({ splits, isRunning, className = '' }: SplitsTableProps) {
  // Calculate averages
  const averages = useMemo(() => {
    if (splits.length === 0) return null;

    const avgHR = splits.filter(s => s.avg_hr).reduce((sum, s) => sum + (s.avg_hr || 0), 0) / splits.filter(s => s.avg_hr).length;
    const avgPace = splits.filter(s => s.avg_pace_sec_km).reduce((sum, s) => sum + (s.avg_pace_sec_km || 0), 0) / splits.filter(s => s.avg_pace_sec_km).length;
    const avgSpeed = splits.filter(s => s.avg_speed_kmh).reduce((sum, s) => sum + (s.avg_speed_kmh || 0), 0) / splits.filter(s => s.avg_speed_kmh).length;

    return {
      avgHR: avgHR || null,
      avgPace: avgPace || null,
      avgSpeed: avgSpeed || null,
    };
  }, [splits]);

  // Find fastest/slowest split
  const { fastestIdx, slowestIdx } = useMemo(() => {
    if (splits.length === 0) return { fastestIdx: -1, slowestIdx: -1 };

    let fastest = 0;
    let slowest = 0;

    if (isRunning) {
      // For running, lower pace is faster
      let minPace = Infinity;
      let maxPace = 0;
      splits.forEach((s, i) => {
        if (s.avg_pace_sec_km && s.avg_pace_sec_km < minPace) {
          minPace = s.avg_pace_sec_km;
          fastest = i;
        }
        if (s.avg_pace_sec_km && s.avg_pace_sec_km > maxPace) {
          maxPace = s.avg_pace_sec_km;
          slowest = i;
        }
      });
    } else {
      // For cycling, higher speed is faster
      let maxSpeed = 0;
      let minSpeed = Infinity;
      splits.forEach((s, i) => {
        if (s.avg_speed_kmh && s.avg_speed_kmh > maxSpeed) {
          maxSpeed = s.avg_speed_kmh;
          fastest = i;
        }
        if (s.avg_speed_kmh && s.avg_speed_kmh < minSpeed) {
          minSpeed = s.avg_speed_kmh;
          slowest = i;
        }
      });
    }

    return { fastestIdx: fastest, slowestIdx: slowest };
  }, [splits, isRunning]);

  if (splits.length === 0) {
    return null;
  }

  const speedLabel = isRunning ? 'Pace' : 'Speed';
  const speedUnit = isRunning ? '/km' : 'km/h';

  return (
    <div className={`bg-gray-900 rounded-xl border border-gray-800 p-4 ${className}`}>
      <div className="flex items-center gap-2 mb-4">
        <svg className="w-5 h-5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <h3 className="text-sm font-medium text-gray-200">Splits</h3>
      </div>

      <div className="overflow-x-auto -mx-4 px-4">
        <table className="w-full text-sm min-w-[500px]">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left py-2 px-2 text-gray-500 font-medium text-xs">Split</th>
              <th className="text-right py-2 px-2 text-gray-500 font-medium text-xs">Dist</th>
              <th className="text-right py-2 px-2 text-gray-500 font-medium text-xs">Time</th>
              <th className="text-right py-2 px-2 text-gray-500 font-medium text-xs">{speedLabel}</th>
              <th className="text-right py-2 px-2 text-gray-500 font-medium text-xs">HR</th>
              <th className="text-right py-2 px-2 text-gray-500 font-medium text-xs hidden sm:table-cell">Elev</th>
            </tr>
          </thead>
          <tbody>
            {splits.map((split, idx) => {
              const isFastest = idx === fastestIdx;
              const isSlowest = idx === slowestIdx;

              return (
                <tr
                  key={split.split_number}
                  className={`border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors ${
                    isFastest ? 'bg-green-900/10' : isSlowest ? 'bg-red-900/10' : ''
                  }`}
                >
                  <td className="py-2 px-2 text-gray-300 font-medium">
                    <span className="flex items-center gap-1">
                      {split.split_number}
                      {isFastest && (
                        <svg className="w-3 h-3 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M5.293 7.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 5.414V17a1 1 0 11-2 0V5.414L6.707 7.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                      {isSlowest && (
                        <svg className="w-3 h-3 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M14.707 12.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 14.586V3a1 1 0 012 0v11.586l2.293-2.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </span>
                  </td>
                  <td className="py-2 px-2 text-right text-gray-400 text-xs">
                    {(split.distance_m / 1000).toFixed(2)} km
                  </td>
                  <td className="py-2 px-2 text-right text-gray-400 text-xs">
                    {formatDuration(split.duration_sec)}
                  </td>
                  <td className={`py-2 px-2 text-right font-medium text-xs ${
                    isFastest ? 'text-green-400' : isSlowest ? 'text-red-400' : 'text-teal-400'
                  }`}>
                    {isRunning
                      ? split.avg_pace_sec_km
                        ? `${formatPace(split.avg_pace_sec_km)}`
                        : '-'
                      : split.avg_speed_kmh
                        ? `${split.avg_speed_kmh.toFixed(1)}`
                        : '-'
                    }
                    <span className="text-gray-500 ml-0.5">{isRunning ? '' : ' km/h'}</span>
                  </td>
                  <td className="py-2 px-2 text-right text-gray-400 text-xs">
                    {split.avg_hr ? `${split.avg_hr}` : '-'}
                  </td>
                  <td className="py-2 px-2 text-right text-gray-500 text-xs hidden sm:table-cell">
                    {split.elevation_gain_m != null ? (
                      <span className="flex items-center justify-end gap-1">
                        <span className="text-green-500">+{Math.round(split.elevation_gain_m)}</span>
                        {split.elevation_loss_m != null && (
                          <span className="text-red-500">-{Math.round(split.elevation_loss_m)}</span>
                        )}
                      </span>
                    ) : '-'}
                  </td>
                </tr>
              );
            })}
          </tbody>
          {averages && (
            <tfoot>
              <tr className="border-t border-gray-700 bg-gray-800/30">
                <td className="py-2 px-2 text-gray-300 font-medium text-xs">Avg</td>
                <td className="py-2 px-2"></td>
                <td className="py-2 px-2"></td>
                <td className="py-2 px-2 text-right text-teal-400 font-medium text-xs">
                  {isRunning
                    ? averages.avgPace
                      ? formatPace(averages.avgPace)
                      : '-'
                    : averages.avgSpeed
                      ? `${averages.avgSpeed.toFixed(1)} km/h`
                      : '-'
                  }
                </td>
                <td className="py-2 px-2 text-right text-gray-400 text-xs">
                  {averages.avgHR ? Math.round(averages.avgHR) : '-'}
                </td>
                <td className="py-2 px-2 hidden sm:table-cell"></td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </div>
  );
}

export default SplitsTable;
