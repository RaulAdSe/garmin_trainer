'use client';

import { useTranslations } from 'next-intl';
import { useSocialProof } from '@/hooks/useSocialProof';
import { Users, TrendingUp, Activity } from 'lucide-react';

interface SocialProofBannerProps {
  className?: string;
  variant?: 'compact' | 'full';
}

/**
 * SocialProofBanner displays community statistics at the top of pages
 * to create a sense of belonging and motivation.
 *
 * Shows:
 * - Number of athletes who trained today
 * - User's top percentile ranking (if available)
 */
export function SocialProofBanner({
  className = '',
  variant = 'compact',
}: SocialProofBannerProps) {
  const t = useTranslations('socialProof');
  const { data, isLoading, error } = useSocialProof();

  // Don't show anything if loading or error
  if (isLoading || error || !data) {
    return null;
  }

  // Find the best percentile to show
  const percentiles = [
    data.pacePercentile,
    data.streakPercentile,
    data.levelPercentile,
  ].filter(Boolean);

  const bestPercentile = percentiles.reduce(
    (best, current) => {
      if (!current) return best;
      if (!best) return current;
      return current.percentile > best.percentile ? current : best;
    },
    null as typeof percentiles[0]
  );

  if (variant === 'compact') {
    return (
      <div
        className={`
          flex items-center justify-between gap-4 px-4 py-2
          bg-gradient-to-r from-blue-50/80 to-indigo-50/80
          dark:from-blue-900/20 dark:to-indigo-900/20
          border-b border-blue-100/50 dark:border-blue-800/30
          text-sm text-slate-600 dark:text-slate-300
          ${className}
        `}
      >
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-blue-500" aria-hidden="true" />
          <span>
            <span className="font-semibold text-blue-600 dark:text-blue-400">
              {data.athletesTrainedToday.toLocaleString()}
            </span>{' '}
            {t('athletesTrained')}
          </span>
        </div>

        {bestPercentile && (
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-green-500" aria-hidden="true" />
            <span className="text-green-600 dark:text-green-400 font-medium">
              {t('topPercentile', { percentile: 100 - bestPercentile.percentile })}
            </span>
          </div>
        )}
      </div>
    );
  }

  // Full variant with more details
  return (
    <div
      className={`
        rounded-xl p-4
        bg-gradient-to-br from-blue-50 to-indigo-50
        dark:from-blue-900/30 dark:to-indigo-900/30
        border border-blue-100/50 dark:border-blue-800/30
        ${className}
      `}
    >
      <div className="flex items-center justify-between flex-wrap gap-4">
        {/* Athletes trained today */}
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-full bg-blue-100 dark:bg-blue-800/50">
            <Users className="h-5 w-5 text-blue-600 dark:text-blue-400" aria-hidden="true" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900 dark:text-white">
              {data.athletesTrainedToday.toLocaleString()}
            </div>
            <div className="text-sm text-slate-500 dark:text-slate-400">
              {t('athletesTrained')}
            </div>
          </div>
        </div>

        {/* Workouts completed */}
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-full bg-emerald-100 dark:bg-emerald-800/50">
            <Activity className="h-5 w-5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900 dark:text-white">
              {data.workoutsCompletedToday.toLocaleString()}
            </div>
            <div className="text-sm text-slate-500 dark:text-slate-400">
              {t('workoutsToday')}
            </div>
          </div>
        </div>

        {/* Best percentile */}
        {bestPercentile && (
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-full bg-amber-100 dark:bg-amber-800/50">
              <TrendingUp className="h-5 w-5 text-amber-600 dark:text-amber-400" aria-hidden="true" />
            </div>
            <div>
              <div className="text-2xl font-bold text-slate-900 dark:text-white">
                {t('topPercentile', { percentile: 100 - bestPercentile.percentile })}
              </div>
              <div className="text-sm text-slate-500 dark:text-slate-400">
                {t(`category.${bestPercentile.category}`)}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default SocialProofBanner;
