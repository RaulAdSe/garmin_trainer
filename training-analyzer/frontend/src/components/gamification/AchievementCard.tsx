'use client';

import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/Card';
import { AchievementBadge, type Achievement, type AchievementRarity } from './AchievementBadge';

interface AchievementCardProps {
  achievement: Achievement;
  className?: string;
  onClick?: () => void;
}

const rarityColors: Record<AchievementRarity, { text: string; bg: string; border: string }> = {
  common: {
    text: 'text-gray-400',
    bg: 'bg-gray-700/50',
    border: 'border-gray-600',
  },
  rare: {
    text: 'text-blue-400',
    bg: 'bg-blue-900/30',
    border: 'border-blue-700',
  },
  epic: {
    text: 'text-purple-400',
    bg: 'bg-purple-900/30',
    border: 'border-purple-700',
  },
  legendary: {
    text: 'text-amber-400',
    bg: 'bg-amber-900/30',
    border: 'border-amber-700',
  },
};

const rarityLabels: Record<AchievementRarity, string> = {
  common: 'Common',
  rare: 'Rare',
  epic: 'Epic',
  legendary: 'Legendary',
};

export function AchievementCard({ achievement, className, onClick }: AchievementCardProps) {
  const isLocked = !achievement.unlocked;
  const rarityStyle = rarityColors[achievement.rarity];
  const hasProgress = achievement.progress !== undefined && achievement.progress_max !== undefined;
  const progressPercent = hasProgress
    ? Math.min((achievement.progress! / achievement.progress_max!) * 100, 100)
    : 0;

  return (
    <Card
      variant={onClick ? 'interactive' : 'default'}
      padding="sm"
      className={cn(
        'relative overflow-hidden transition-all duration-200',
        isLocked && 'opacity-70',
        className
      )}
      onClick={onClick}
    >
      <div className="flex gap-4">
        {/* Badge */}
        <div className="shrink-0">
          <AchievementBadge
            achievement={achievement}
            size="lg"
            showTooltip={false}
          />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Header: Name + Rarity */}
          <div className="flex items-start justify-between gap-2 mb-1">
            <h3
              className={cn(
                'font-semibold text-sm truncate',
                isLocked ? 'text-gray-400' : 'text-gray-100'
              )}
            >
              {achievement.name}
            </h3>
            <span
              className={cn(
                'shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded border',
                rarityStyle.text,
                rarityStyle.bg,
                rarityStyle.border
              )}
            >
              {rarityLabels[achievement.rarity]}
            </span>
          </div>

          {/* Description */}
          <p className="text-xs text-gray-500 line-clamp-2 mb-2">
            {achievement.description}
          </p>

          {/* Progress bar (for partially complete achievements) */}
          {hasProgress && !achievement.unlocked && (
            <div className="mb-2">
              <div className="flex items-center justify-between text-[10px] mb-1">
                <span className="text-gray-500">Progress</span>
                <span className="text-gray-400">
                  {achievement.progress}/{achievement.progress_max}
                </span>
              </div>
              <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-teal-500 to-green-500 rounded-full transition-all duration-500"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>
          )}

          {/* XP Value */}
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'text-xs font-medium',
                isLocked ? 'text-gray-500' : 'text-teal-400'
              )}
            >
              +{achievement.xp_value} XP
            </span>
            {achievement.unlocked && achievement.unlocked_at && (
              <span className="text-[10px] text-gray-600">
                Unlocked {formatUnlockedDate(achievement.unlocked_at)}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Unlocked glow effect */}
      {!isLocked && achievement.rarity !== 'common' && (
        <div
          className={cn(
            'absolute inset-0 pointer-events-none opacity-10',
            achievement.rarity === 'rare' && 'bg-gradient-to-br from-blue-400 to-transparent',
            achievement.rarity === 'epic' && 'bg-gradient-to-br from-purple-400 to-transparent',
            achievement.rarity === 'legendary' && 'bg-gradient-to-br from-amber-400 to-transparent'
          )}
        />
      )}
    </Card>
  );
}

// Helper function to format unlock date
function formatUnlockedDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'today';
  if (diffDays === 1) return 'yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;

  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Skeleton loader
export function AchievementCardSkeleton() {
  return (
    <Card padding="sm" className="animate-pulse">
      <div className="flex gap-4">
        <div className="w-20 h-20 rounded-full bg-gray-800" />
        <div className="flex-1 space-y-2">
          <div className="flex justify-between">
            <div className="h-4 w-24 bg-gray-800 rounded" />
            <div className="h-4 w-12 bg-gray-800 rounded" />
          </div>
          <div className="h-3 w-full bg-gray-800 rounded" />
          <div className="h-3 w-3/4 bg-gray-800 rounded" />
          <div className="h-3 w-16 bg-gray-800 rounded" />
        </div>
      </div>
    </Card>
  );
}

export default AchievementCard;
