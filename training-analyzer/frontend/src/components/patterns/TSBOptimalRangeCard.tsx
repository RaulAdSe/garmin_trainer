'use client';

import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui/Card';
import type { TSBOptimalRange } from '@/types/patterns';

interface TSBOptimalRangeCardProps {
  data?: TSBOptimalRange | null;
}

export function TSBOptimalRangeCard({ data }: TSBOptimalRangeCardProps) {
  const t = useTranslations('patterns');

  if (!data || data.optimal_tsb_min === undefined || data.optimal_tsb_max === undefined) {
    return (
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">Optimal TSB Range</h3>
        <div className="text-center py-8">
          <p className="text-gray-400">{t('noData')}</p>
        </div>
      </Card>
    );
  }

  const rangeMin = data.optimal_tsb_min;
  const rangeMax = data.optimal_tsb_max;
  const rangeWidth = rangeMax - rangeMin;

  // Get the optimal zone stats for performance info
  const optimalZoneStats = data.zone_stats?.find((z) => z.zone === data.optimal_zone);

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold text-gray-100 mb-4">Optimal TSB Range</h3>

      <div className="space-y-4">
        {/* Range Visualization */}
        <div className="relative">
          <div className="h-8 bg-gray-800 rounded-lg relative overflow-hidden">
            {/* Optimal Range */}
            <div
              className="absolute h-full bg-teal-500/30 border-y border-teal-500"
              style={{
                left: '0%',
                width: '100%',
              }}
            />
          </div>
          <div className="flex justify-between mt-2 text-xs text-gray-500">
            <span>{rangeMin.toFixed(1)}</span>
            <span className="font-medium text-teal-400">{data.optimal_zone || 'Optimal'}</span>
            <span>{rangeMax.toFixed(1)}</span>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-gray-500 mb-1">Optimal Min</p>
            <p className="text-lg font-semibold text-gray-200">{rangeMin.toFixed(1)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Optimal Max</p>
            <p className="text-lg font-semibold text-gray-200">{rangeMax.toFixed(1)}</p>
          </div>
        </div>

        {/* Performance Stats */}
        {optimalZoneStats?.avg_performance !== undefined && (
          <div className="p-3 bg-gray-800/50 rounded-lg">
            <p className="text-sm text-gray-400 mb-1">Average Performance in Range</p>
            <p className="text-xl font-bold text-teal-400">
              {(optimalZoneStats.avg_performance * 100).toFixed(1)}%
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Based on {optimalZoneStats.workout_count} workouts
            </p>
          </div>
        )}

      </div>
    </Card>
  );
}
