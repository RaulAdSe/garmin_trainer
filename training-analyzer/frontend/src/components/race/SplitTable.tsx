'use client';

import React, { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui';
import type { SplitTarget } from '@/lib/types';

interface SplitTableProps {
  splits: SplitTarget[];
  showNotes?: boolean;
  showElevation?: boolean;
}

export default function SplitTable({
  splits,
  showNotes = true,
  showElevation = true,
}: SplitTableProps) {
  const t = useTranslations('racePacing');
  const [expandedSplit, setExpandedSplit] = useState<number | null>(null);

  if (!splits || splits.length === 0) {
    return null;
  }

  // Check if any splits have elevation adjustments
  const hasElevation = showElevation && splits.some((s) => s.elevation_adjustment_pct !== 0);

  return (
    <Card className="overflow-hidden">
      <div className="p-4 border-b border-gray-700">
        <h3 className="text-lg font-semibold text-white">{t('splitTargets')}</h3>
        <p className="text-sm text-gray-400">{t('perKmSplits')}</p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-800/50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                {t('km')}
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                {t('targetPace')}
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                {t('cumulativeTime')}
              </th>
              {hasElevation && (
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  {t('elevation')}
                </th>
              )}
              {showNotes && (
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  {t('notes')}
                </th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {splits.map((split, index) => {
              const isExpanded = expandedSplit === split.split_number;
              const elevAdjust = split.elevation_adjustment_pct;
              const isUphill = elevAdjust > 0;
              const isDownhill = elevAdjust < 0;

              return (
                <React.Fragment key={split.split_number}>
                  <tr
                    className={`hover:bg-gray-800/30 transition-colors ${
                      isExpanded ? 'bg-gray-800/50' : ''
                    }`}
                    onClick={() =>
                      setExpandedSplit(isExpanded ? null : split.split_number)
                    }
                  >
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="text-white font-medium">
                        {split.distance_km.toFixed(2)}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <span className="text-orange-500 font-mono font-medium">
                          {split.target_pace_formatted}
                        </span>
                        <span className="text-gray-500 text-sm">/km</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="text-gray-300 font-mono">
                        {split.cumulative_time_formatted}
                      </span>
                    </td>
                    {hasElevation && (
                      <td className="px-4 py-3 whitespace-nowrap">
                        {elevAdjust !== 0 && (
                          <span
                            className={`text-sm ${
                              isUphill ? 'text-red-400' : 'text-green-400'
                            }`}
                          >
                            {isUphill ? '+' : ''}
                            {elevAdjust.toFixed(1)}%
                            <span className="ml-1">
                              {isUphill ? '\u2191' : '\u2193'}
                            </span>
                          </span>
                        )}
                      </td>
                    )}
                    {showNotes && (
                      <td className="px-4 py-3">
                        <span className="text-gray-400 text-sm truncate max-w-xs block">
                          {split.notes || '-'}
                        </span>
                      </td>
                    )}
                  </tr>

                  {/* Expanded row for mobile notes */}
                  {isExpanded && split.notes && (
                    <tr className="bg-gray-800/30">
                      <td colSpan={hasElevation ? 5 : 4} className="px-4 py-3">
                        <div className="text-sm text-gray-400">
                          <span className="font-medium text-gray-300">
                            {t('notes')}:
                          </span>{' '}
                          {split.notes}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Summary row */}
      <div className="p-4 bg-gray-800/30 border-t border-gray-700">
        <div className="flex justify-between items-center text-sm">
          <span className="text-gray-400">{t('totalSplits', { count: splits.length })}</span>
          <span className="text-white font-medium">
            {t('finishTime')}: {splits[splits.length - 1]?.cumulative_time_formatted}
          </span>
        </div>
      </div>
    </Card>
  );
}
