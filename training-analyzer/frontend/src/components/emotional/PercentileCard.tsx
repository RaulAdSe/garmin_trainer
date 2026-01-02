'use client';

import { useTranslations } from 'next-intl';
import { Tooltip } from '@/components/ui/Tooltip';
import { Zap, Flame, Award, TrendingUp } from 'lucide-react';

interface PercentileRanking {
  category: string;
  percentile: number;
  label: string;
  value?: number;
  unit?: string;
}

interface PercentileCardProps {
  pacePercentile?: PercentileRanking | null;
  streakPercentile?: PercentileRanking | null;
  levelPercentile?: PercentileRanking | null;
  className?: string;
}

/**
 * PercentileCard shows the user's percentile rankings across different categories.
 * Features progress bar visualizations and tooltips with details.
 */
export function PercentileCard({
  pacePercentile,
  streakPercentile,
  levelPercentile,
  className = '',
}: PercentileCardProps) {
  const t = useTranslations('socialProof');

  const percentiles = [
    { data: pacePercentile, icon: Zap, color: 'blue' },
    { data: streakPercentile, icon: Flame, color: 'orange' },
    { data: levelPercentile, icon: Award, color: 'purple' },
  ].filter((p) => p.data !== null && p.data !== undefined);

  if (percentiles.length === 0) {
    return null;
  }

  return (
    <div
      className={`
        rounded-xl p-4
        bg-white dark:bg-slate-800
        border border-slate-200 dark:border-slate-700
        shadow-sm
        ${className}
      `}
    >
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp className="h-5 w-5 text-slate-500" aria-hidden="true" />
        <h3 className="font-semibold text-slate-900 dark:text-white">
          {t('rankings.title')}
        </h3>
      </div>

      <div className="space-y-4">
        {percentiles.map(({ data, icon: Icon, color }) => {
          if (!data) return null;

          const colorClasses = getColorClasses(color);

          return (
            <Tooltip
              key={data.category}
              content={
                <div className="text-sm">
                  <div className="font-medium">{t(`category.${data.category}`)}</div>
                  {data.value !== undefined && (
                    <div className="text-slate-300">
                      {formatValue(data.value, data.unit)}
                    </div>
                  )}
                  <div className="mt-1 text-slate-400">{data.label}</div>
                </div>
              }
            >
              <div className="cursor-help">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <Icon
                      className={`h-4 w-4 ${colorClasses.icon}`}
                      aria-hidden="true"
                    />
                    <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                      {t(`category.${data.category}`)}
                    </span>
                  </div>
                  <span className={`text-sm font-semibold ${colorClasses.text}`}>
                    {t('topPercentile', { percentile: 100 - data.percentile })}
                  </span>
                </div>

                {/* Progress bar */}
                <div className="h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${colorClasses.bar}`}
                    style={{ width: `${data.percentile}%` }}
                    role="progressbar"
                    aria-valuenow={data.percentile}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label={`${data.percentile}th percentile for ${data.category}`}
                  />
                </div>
              </div>
            </Tooltip>
          );
        })}
      </div>
    </div>
  );
}

function getColorClasses(color: string): {
  icon: string;
  text: string;
  bar: string;
} {
  switch (color) {
    case 'blue':
      return {
        icon: 'text-blue-500',
        text: 'text-blue-600 dark:text-blue-400',
        bar: 'bg-gradient-to-r from-blue-400 to-blue-600',
      };
    case 'orange':
      return {
        icon: 'text-orange-500',
        text: 'text-orange-600 dark:text-orange-400',
        bar: 'bg-gradient-to-r from-orange-400 to-orange-600',
      };
    case 'purple':
      return {
        icon: 'text-purple-500',
        text: 'text-purple-600 dark:text-purple-400',
        bar: 'bg-gradient-to-r from-purple-400 to-purple-600',
      };
    default:
      return {
        icon: 'text-slate-500',
        text: 'text-slate-600 dark:text-slate-400',
        bar: 'bg-gradient-to-r from-slate-400 to-slate-600',
      };
  }
}

function formatValue(value: number, unit?: string): string {
  if (unit === 'min/km') {
    const minutes = Math.floor(value);
    const seconds = Math.round((value - minutes) * 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')} min/km`;
  }
  if (unit === 'days') {
    return `${value} days`;
  }
  return value.toString();
}

export default PercentileCard;
