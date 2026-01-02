'use client';

import { useTranslations } from 'next-intl';
import { useSocialProof } from '@/hooks/useSocialProof';
import { Activity, Users, Zap, Award, Flame } from 'lucide-react';
import { useEffect, useState } from 'react';

interface CommunityPulseProps {
  className?: string;
  showActivityFeed?: boolean;
}

/**
 * CommunityPulse shows a live-ish indicator of community activity.
 * Features an animated pulse effect and optional activity feed.
 */
export function CommunityPulse({
  className = '',
  showActivityFeed = true,
}: CommunityPulseProps) {
  const t = useTranslations('socialProof');
  const { data, isLoading, refetch } = useSocialProof();
  const [pulseActive, setPulseActive] = useState(false);

  // Animate pulse effect periodically
  useEffect(() => {
    const interval = setInterval(() => {
      setPulseActive(true);
      setTimeout(() => setPulseActive(false), 1000);
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  // Refresh data periodically (every 60 seconds)
  useEffect(() => {
    const interval = setInterval(() => {
      refetch();
    }, 60000);

    return () => clearInterval(interval);
  }, [refetch]);

  if (isLoading || !data) {
    return null;
  }

  const activityTypeIcons: Record<string, typeof Activity> = {
    workout_completed: Activity,
    achievement_unlocked: Award,
    streak_continued: Flame,
    level_up: Zap,
  };

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
      {/* Live indicator */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative">
          <div
            className={`
              w-3 h-3 rounded-full bg-green-500
              ${pulseActive ? 'animate-ping' : ''}
            `}
          />
          <div
            className="absolute inset-0 w-3 h-3 rounded-full bg-green-500"
            aria-hidden="true"
          />
        </div>
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-slate-500" aria-hidden="true" />
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
            <span className="text-green-600 dark:text-green-400 font-semibold">
              {data.athletesTrainingNow}
            </span>{' '}
            {t('trainingNow')}
          </span>
        </div>
      </div>

      {/* Activity feed */}
      {showActivityFeed && data.recentActivity && data.recentActivity.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
            {t('recentActivity')}
          </h4>
          <div className="space-y-1.5">
            {data.recentActivity.slice(0, 4).map((activity, index) => {
              const Icon = activityTypeIcons[activity.activityType] || Activity;

              return (
                <div
                  key={`${activity.activityType}-${index}`}
                  className="flex items-center justify-between text-sm"
                >
                  <div className="flex items-center gap-2">
                    <Icon
                      className="h-3.5 w-3.5 text-slate-400"
                      aria-hidden="true"
                    />
                    <span className="text-slate-600 dark:text-slate-400">
                      <span className="font-medium text-slate-700 dark:text-slate-300">
                        {activity.count}
                      </span>{' '}
                      {t(`activityTypes.${activity.activityType}`)}
                    </span>
                  </div>
                  <span className="text-xs text-slate-400 dark:text-slate-500">
                    {activity.timeAgo}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Quick stats */}
      <div
        className="
          mt-4 pt-4
          border-t border-slate-100 dark:border-slate-700
          flex items-center justify-between
        "
      >
        <div className="text-center">
          <div className="text-lg font-bold text-slate-900 dark:text-white">
            {data.athletesTrainedToday.toLocaleString()}
          </div>
          <div className="text-xs text-slate-500 dark:text-slate-400">
            {t('athletesToday')}
          </div>
        </div>
        <div className="w-px h-8 bg-slate-200 dark:bg-slate-700" />
        <div className="text-center">
          <div className="text-lg font-bold text-slate-900 dark:text-white">
            {data.workoutsCompletedToday.toLocaleString()}
          </div>
          <div className="text-xs text-slate-500 dark:text-slate-400">
            {t('workoutsToday')}
          </div>
        </div>
      </div>
    </div>
  );
}

export default CommunityPulse;
