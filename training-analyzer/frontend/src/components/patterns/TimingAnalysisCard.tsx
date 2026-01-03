'use client';

import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui/Card';
import type { TimingAnalysis } from '@/types/patterns';

interface TimingAnalysisCardProps {
  data?: TimingAnalysis | null;
}

export function TimingAnalysisCard({ data }: TimingAnalysisCardProps) {
  const t = useTranslations('patterns');

  if (!data || data.total_workouts_analyzed < 10) {
    return (
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">Timing Analysis</h3>
        <div className="text-center py-8">
          <p className="text-gray-400">
            {data?.total_workouts_analyzed
              ? t('insufficientData', { count: data.total_workouts_analyzed })
              : t('noData')}
          </p>
        </div>
      </Card>
    );
  }

  const formatLabel = (value: string): string => {
    return value.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  };

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold text-gray-100 mb-4">Optimal Training Times</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Best Time of Day */}
        {data.best_time_slot && (
          <div className="p-4 bg-gray-800/50 rounded-lg">
            <p className="text-sm text-gray-400 mb-2">Best Time of Day</p>
            <p className="text-2xl font-bold text-teal-400 mb-1">
              {formatLabel(data.best_time_slot)}
            </p>
            <p className="text-sm text-gray-500">
              Performance Boost: +{data.best_time_slot_boost.toFixed(1)}%
            </p>
          </div>
        )}

        {/* Best Day of Week */}
        {data.best_day && (
          <div className="p-4 bg-gray-800/50 rounded-lg">
            <p className="text-sm text-gray-400 mb-2">Best Day of Week</p>
            <p className="text-2xl font-bold text-teal-400 mb-1">
              {formatLabel(data.best_day)}
            </p>
            <p className="text-sm text-gray-500">
              Performance Boost: +{data.best_day_boost.toFixed(1)}%
            </p>
          </div>
        )}
      </div>

      {/* Data Quality */}
      <div className="mt-4 pt-4 border-t border-gray-800">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-400">Data Quality</span>
          <span className="text-sm font-medium text-gray-300">
            {(data.data_quality_score * 100).toFixed(0)}%
          </span>
        </div>
        <div className="mt-2 h-2 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-teal-500 transition-all duration-500"
            style={{ width: `${data.data_quality_score * 100}%` }}
          />
        </div>
      </div>
    </Card>
  );
}

