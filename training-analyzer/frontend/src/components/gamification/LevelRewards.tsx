'use client';

import { cn } from '@/lib/utils';
import { useTranslations } from 'next-intl';
import { LevelBadge } from './LevelBadge';

interface LevelReward {
  level: number;
  name: string;
  title: string;
  unlocks: string[];
  description: string;
}

interface LevelRewardsProps {
  currentLevel: number;
  nextReward?: LevelReward | null;
  unlockedFeatures?: string[];
  className?: string;
}

// Core features always available - never locked
const ALWAYS_AVAILABLE_FEATURES = [
  'basic_dashboard',
  'workout_history',
  'ai_workout_analysis',
  'garmin_sync',
];

// All level rewards for the roadmap
const ALL_LEVEL_REWARDS: LevelReward[] = [
  {
    level: 1,
    name: 'Rookie',
    title: 'Training Rookie',
    unlocks: [], // Core features always available
    description: 'Welcome! Start your training journey.',
  },
  {
    level: 3,
    name: 'Learner',
    title: 'Eager Learner',
    unlocks: ['trend_analysis'],
    description: 'Trend analysis (7/30/90 day views) unlocked!',
  },
  {
    level: 5,
    name: 'Dedicated',
    title: 'Dedicated Athlete',
    unlocks: ['advanced_metrics'],
    description: 'Advanced metrics and fatigue modeling unlocked!',
  },
  {
    level: 8,
    name: 'Committed',
    title: 'Committed Trainer',
    unlocks: ['ai_coach_chat', 'personalized_tips'],
    description: 'AI Coach chat and personalized tips unlocked!',
  },
  {
    level: 10,
    name: 'Athlete',
    title: 'Serious Athlete',
    unlocks: ['training_plan_generation', 'race_predictions'],
    description: 'Training plan generation and race predictions unlocked!',
  },
  {
    level: 15,
    name: 'Advanced',
    title: 'Advanced Performer',
    unlocks: ['custom_workout_design', 'garmin_fit_export'],
    description: 'Custom workout design with Garmin FIT export unlocked!',
  },
  {
    level: 20,
    name: 'Expert',
    title: 'Training Expert',
    unlocks: ['periodization_planner', 'peak_optimization'],
    description: 'Periodization planner and peak optimization unlocked!',
  },
  {
    level: 25,
    name: 'Elite',
    title: 'Elite Performer',
    unlocks: ['coach_mode', 'athlete_management'],
    description: 'Coach mode unlocked - help others train!',
  },
  {
    level: 30,
    name: 'Master',
    title: 'Training Master',
    unlocks: ['beta_access'],
    description: 'All features unlocked + early access to new features!',
  },
];

// Export for use in other components (e.g., feature gating)
export { ALWAYS_AVAILABLE_FEATURES };

export function LevelRewards({
  currentLevel,
  nextReward,
  unlockedFeatures = [],
  className,
}: LevelRewardsProps) {
  const t = useTranslations('achievements.levelRewards');

  return (
    <div className={cn('space-y-6', className)}>
      {/* Current Status */}
      <div className="bg-gray-900/50 rounded-xl p-4 border border-gray-800">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-300">{t('currentTitle')}</p>
            <p className="text-lg font-semibold text-white">
              {t(`levels.${getCurrentTierLevel(currentLevel)}.title`)}
            </p>
          </div>
          <LevelBadge level={currentLevel} size="lg" showTooltip={false} />
        </div>
      </div>

      {/* Always Available Features */}
      <div className="bg-teal-500/10 rounded-xl p-4 border border-teal-500/30">
        <p className="text-sm text-teal-400 font-medium mb-2">{t('alwaysAvailable')}</p>
        <div className="flex flex-wrap gap-2">
          {ALWAYS_AVAILABLE_FEATURES.map((feature) => (
            <span
              key={feature}
              className="text-xs px-2 py-1 bg-teal-500/20 text-teal-300 rounded-full"
            >
              {t(`features.${feature}`)}
            </span>
          ))}
        </div>
      </div>

      {/* Next Reward Preview */}
      {nextReward && (
        <div className="bg-gradient-to-r from-orange-500/10 to-amber-500/10 rounded-xl p-4 border border-orange-500/30">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0">
              <div className="w-12 h-12 rounded-full bg-orange-500/20 flex items-center justify-center">
                <span className="text-2xl">🎁</span>
              </div>
            </div>
            <div className="flex-1">
              <p className="text-sm text-orange-400 font-medium">
                {t('nextReward')} - {t('unlocksAt')} {nextReward.level}
              </p>
              <p className="text-white font-semibold mt-1">{nextReward.title}</p>
              <p className="text-sm text-gray-300 mt-1">{nextReward.description}</p>
              <div className="flex flex-wrap gap-2 mt-2">
                {nextReward.unlocks.map((feature) => (
                  <span
                    key={feature}
                    className="text-xs px-2 py-1 bg-orange-500/20 text-orange-300 rounded-full"
                  >
                    {t(`features.${feature}`)}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Level Roadmap */}
      <div>
        <h3 className="text-sm font-medium text-gray-300 mb-4">{t('title')}</h3>
        <div className="space-y-3">
          {ALL_LEVEL_REWARDS.map((reward, index) => {
            const isUnlocked = currentLevel >= reward.level;
            const isCurrent =
              currentLevel >= reward.level &&
              (index === ALL_LEVEL_REWARDS.length - 1 ||
                currentLevel < ALL_LEVEL_REWARDS[index + 1].level);
            const isNext = nextReward?.level === reward.level;

            return (
              <LevelRewardItem
                key={reward.level}
                reward={reward}
                isUnlocked={isUnlocked}
                isCurrent={isCurrent}
                isNext={isNext}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}

interface LevelRewardItemProps {
  reward: LevelReward;
  isUnlocked: boolean;
  isCurrent: boolean;
  isNext: boolean;
}

function LevelRewardItem({ reward, isUnlocked, isCurrent, isNext }: LevelRewardItemProps) {
  const t = useTranslations('achievements.levelRewards');

  return (
    <div
      className={cn(
        'relative flex items-center gap-4 p-3 rounded-lg transition-all duration-200',
        isUnlocked
          ? 'bg-gray-800/50 border border-gray-700'
          : 'bg-gray-900/30 border border-gray-800/50 opacity-60',
        isCurrent && 'ring-2 ring-orange-500/50 border-orange-500/30',
        isNext && 'border-orange-500/50 opacity-100'
      )}
    >
      {/* Level indicator */}
      <div className="flex-shrink-0">
        <LevelBadge
          level={reward.level}
          size="sm"
          showTooltip={false}
        />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'font-medium text-sm',
              isUnlocked ? 'text-white' : 'text-gray-500'
            )}
          >
            {reward.title}
          </span>
          {isCurrent && (
            <span className="text-xs px-2 py-0.5 bg-orange-500/20 text-orange-400 rounded-full">
              Current
            </span>
          )}
          {isNext && (
            <span className="text-xs px-2 py-0.5 bg-orange-500/30 text-orange-300 rounded-full animate-pulse">
              Next
            </span>
          )}
        </div>
        <div className="flex flex-wrap gap-1 mt-1">
          {reward.unlocks.slice(0, 3).map((feature) => (
            <span
              key={feature}
              className={cn(
                'text-xs px-1.5 py-0.5 rounded',
                isUnlocked
                  ? 'bg-gray-700 text-gray-300'
                  : 'bg-gray-800 text-gray-500'
              )}
            >
              {t(`features.${feature}`)}
            </span>
          ))}
          {reward.unlocks.length > 3 && (
            <span className="text-xs text-gray-500">
              +{reward.unlocks.length - 3} more
            </span>
          )}
        </div>
      </div>

      {/* Status icon */}
      <div className="flex-shrink-0">
        {isUnlocked ? (
          <svg
            className="w-5 h-5 text-green-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        ) : (
          <svg
            className="w-5 h-5 text-gray-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
            />
          </svg>
        )}
      </div>
    </div>
  );
}

// Helper to get the current tier level for translations
function getCurrentTierLevel(level: number): number {
  const tiers = [1, 3, 5, 8, 10, 15, 20, 25, 30];
  for (let i = tiers.length - 1; i >= 0; i--) {
    if (level >= tiers[i]) {
      return tiers[i];
    }
  }
  return 1;
}

// Compact version for sidebar or header
export function LevelRewardsCompact({
  currentLevel,
  nextReward,
  className,
}: Omit<LevelRewardsProps, 'unlockedFeatures'>) {
  const t = useTranslations('achievements.levelRewards');

  if (!nextReward) {
    return (
      <div className={cn('text-sm text-gray-300', className)}>
        {t('allUnlocked')}
      </div>
    );
  }

  const progress = ((currentLevel - 1) / (nextReward.level - 1)) * 100;

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-300">{t('nextReward')}</span>
        <span className="text-orange-400">Level {nextReward.level}</span>
      </div>
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-orange-500 to-amber-500 transition-all duration-500"
          style={{ width: `${Math.min(progress, 100)}%` }}
        />
      </div>
      <p className="text-xs text-gray-500 truncate">{nextReward.title}</p>
    </div>
  );
}

export default LevelRewards;
