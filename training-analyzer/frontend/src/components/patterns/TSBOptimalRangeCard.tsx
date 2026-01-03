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

  // Get the optimal zone stats for performance info
  const optimalZoneStats = data.zone_stats?.find((z) => z.zone === data.optimal_zone);

  // TSB scale for visualization (-50 to +30)
  const scaleMin = -50;
  const scaleMax = 30;
  const scaleRange = scaleMax - scaleMin;

  // Calculate position and width on the scale
  const leftPercent = ((rangeMin - scaleMin) / scaleRange) * 100;
  const widthPercent = ((rangeMax - rangeMin) / scaleRange) * 100;

  // Zone colors for background gradient
  const zoneColors = [
    { pos: 0, color: 'rgb(239,68,68)' },      // -50: Deep fatigue (red)
    { pos: 31.25, color: 'rgb(245,158,11)' }, // -25: Fatigued (orange)
    { pos: 50, color: 'rgb(234,179,8)' },     // -10: Functional (yellow)
    { pos: 62.5, color: 'rgb(34,197,94)' },   // 0: Fresh (green)
    { pos: 81.25, color: 'rgb(34,211,238)' }, // +15: Peaked (teal)
    { pos: 100, color: 'rgb(147,51,234)' },   // +30: Detrained (purple)
  ];
  const gradient = `linear-gradient(to right, ${zoneColors.map(z => `${z.color} ${z.pos}%`).join(', ')})`;

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold text-gray-100 mb-4">Optimal TSB Range</h3>

      <div className="space-y-4">
        {/* Range Visualization */}
        <div className="relative">
          {/* TSB Scale Background */}
          <div
            className="h-8 rounded-lg relative overflow-hidden opacity-40"
            style={{ background: gradient }}
          />
          {/* Optimal Range Highlight */}
          <div
            className="absolute top-0 h-8 bg-teal-400/60 border-2 border-teal-400 rounded"
            style={{
              left: `${Math.max(0, leftPercent)}%`,
              width: `${Math.min(100 - leftPercent, widthPercent)}%`,
            }}
          />
          {/* Scale labels */}
          <div className="flex justify-between mt-2 text-xs text-gray-500">
            <span>-50</span>
            <span>-25</span>
            <span>0</span>
            <span>+15</span>
            <span>+30</span>
          </div>
        </div>

        {/* Zone Label */}
        <div className="text-center">
          <span className="text-sm text-gray-400">Your optimal zone: </span>
          <span className="text-sm font-semibold text-teal-400 capitalize">
            {data.optimal_zone?.replace('_', ' ') || 'Fresh'}
          </span>
          <span className="text-sm text-gray-400"> ({rangeMin.toFixed(0)} to {rangeMax.toFixed(0)})</span>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-3 gap-3">
          {data.current_tsb !== null && data.current_tsb !== undefined && (
            <div className="p-3 bg-gray-800/50 rounded-lg text-center">
              <p className="text-xs text-gray-500 mb-1">Current TSB</p>
              <p className="text-lg font-semibold text-gray-200">{data.current_tsb.toFixed(1)}</p>
            </div>
          )}
          {data.recommended_taper_days > 0 && (
            <div className="p-3 bg-gray-800/50 rounded-lg text-center">
              <p className="text-xs text-gray-500 mb-1">Taper Days</p>
              <p className="text-lg font-semibold text-gray-200">{data.recommended_taper_days}</p>
            </div>
          )}
          {optimalZoneStats && (
            <div className="p-3 bg-gray-800/50 rounded-lg text-center">
              <p className="text-xs text-gray-500 mb-1">Workouts in Zone</p>
              <p className="text-lg font-semibold text-gray-200">{optimalZoneStats.workout_count}</p>
            </div>
          )}
        </div>

        {/* Performance Stats */}
        {optimalZoneStats?.avg_performance !== undefined && (
          <div className="p-3 bg-gray-800/30 rounded-lg">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Performance in this zone:</span>
              <span className="text-lg font-bold text-teal-400">
                {optimalZoneStats.avg_performance.toFixed(1)}/100
              </span>
            </div>
          </div>
        )}

      </div>
    </Card>
  );
}
