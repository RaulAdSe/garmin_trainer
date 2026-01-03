'use client';

import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui/Card';
import type { SleepDebtResponse } from '@/lib/types';

interface SleepDebtCardProps {
  data?: SleepDebtResponse | null;
}

export function SleepDebtCard({ data }: SleepDebtCardProps) {
  const t = useTranslations('recovery');

  if (!data?.success || !data.data) {
    return (
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">Sleep Debt</h3>
        <div className="text-center py-8">
          <p className="text-gray-400">{data?.error || t('noSleepData')}</p>
        </div>
      </Card>
    );
  }

  const sleepDebt = data.data;
  const debtHours = sleepDebt.totalDebtHours ?? 0;
  const impact = sleepDebt.impactLevel ?? 'minimal';

  // Color based on impact
  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'minimal':
        return 'text-green-400';
      case 'moderate':
        return 'text-yellow-400';
      case 'significant':
        return 'text-orange-400';
      case 'severe':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  };

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold text-gray-100 mb-4">Sleep Debt (7-day rolling)</h3>

      <div className="space-y-4">
        {/* Total Debt */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">Total Debt</span>
            <span className={`text-2xl font-bold ${getImpactColor(impact)}`}>
              {debtHours.toFixed(1)}h
            </span>
          </div>
          <div className="h-3 bg-gray-800 rounded-full overflow-hidden">
            <div
              className={`h-full ${getImpactColor(impact).replace('text-', 'bg-')} transition-all duration-500`}
              style={{ width: `${Math.min((debtHours / 14) * 100, 100)}%` }}
            />
          </div>
        </div>

        {/* Impact Level */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-400">Impact Level</span>
          <span className={`text-sm font-medium ${getImpactColor(impact)}`}>
            {impact.charAt(0).toUpperCase() + impact.slice(1)}
          </span>
        </div>

        {/* Average Sleep */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-400">Average Sleep</span>
          <span className="text-sm text-gray-300">
            {(sleepDebt.averageSleepHours ?? 0).toFixed(1)}h / {sleepDebt.targetHours ?? 8}h target
          </span>
        </div>

        {/* Recommendation */}
        {sleepDebt.recommendation && (
          <div className="mt-4 p-3 bg-gray-800/50 rounded-lg">
            <p className="text-sm text-gray-300">{sleepDebt.recommendation}</p>
          </div>
        )}
      </div>
    </Card>
  );
}

