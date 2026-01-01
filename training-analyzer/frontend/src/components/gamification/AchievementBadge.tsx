'use client';

import { cn } from '@/lib/utils';
import { Tooltip } from '@/components/ui/Tooltip';

export type AchievementRarity = 'common' | 'rare' | 'epic' | 'legendary';

export interface Achievement {
  id: string;
  name: string;
  description: string;
  icon: string;
  rarity: AchievementRarity;
  xp_value: number;
  category: string;
  unlocked: boolean;
  unlocked_at?: string;
  progress?: number;
  progress_max?: number;
}

interface AchievementBadgeProps {
  achievement: Achievement;
  size?: 'sm' | 'md' | 'lg';
  locked?: boolean;
  className?: string;
  showTooltip?: boolean;
}

const sizeConfig = {
  sm: {
    container: 'w-10 h-10',
    icon: 'text-lg',
    lockIcon: 'w-3 h-3',
  },
  md: {
    container: 'w-14 h-14',
    icon: 'text-2xl',
    lockIcon: 'w-4 h-4',
  },
  lg: {
    container: 'w-20 h-20',
    icon: 'text-4xl',
    lockIcon: 'w-5 h-5',
  },
};

const rarityConfig: Record<AchievementRarity, { glow: string; border: string; bg: string }> = {
  common: {
    glow: 'shadow-gray-400/30',
    border: 'border-gray-500',
    bg: 'bg-gray-800',
  },
  rare: {
    glow: 'shadow-blue-400/40',
    border: 'border-blue-500',
    bg: 'bg-blue-900/30',
  },
  epic: {
    glow: 'shadow-purple-400/40',
    border: 'border-purple-500',
    bg: 'bg-purple-900/30',
  },
  legendary: {
    glow: 'shadow-amber-400/50',
    border: 'border-amber-500',
    bg: 'bg-amber-900/30',
  },
};

export function AchievementBadge({
  achievement,
  size = 'md',
  locked,
  className,
  showTooltip = true,
}: AchievementBadgeProps) {
  const config = sizeConfig[size];
  const isLocked = locked ?? !achievement.unlocked;
  const rarityStyles = rarityConfig[achievement.rarity];

  const badge = (
    <div
      className={cn(
        'relative rounded-full flex items-center justify-center border-2 transition-all duration-200',
        config.container,
        isLocked
          ? 'bg-gray-800 border-gray-700 grayscale'
          : cn(rarityStyles.bg, rarityStyles.border, 'shadow-lg', rarityStyles.glow),
        !isLocked && 'hover:scale-105',
        className
      )}
    >
      {/* Icon */}
      <span
        className={cn(
          config.icon,
          isLocked ? 'opacity-40' : 'opacity-100'
        )}
      >
        {achievement.icon}
      </span>

      {/* Lock overlay for locked achievements */}
      {isLocked && (
        <div className="absolute inset-0 flex items-center justify-center rounded-full bg-gray-900/60">
          <svg
            className={cn('text-gray-500', config.lockIcon)}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
            />
          </svg>
        </div>
      )}
    </div>
  );

  if (!showTooltip) {
    return badge;
  }

  const tooltipContent = (
    <div className="space-y-1 max-w-[200px]">
      <div className="font-medium text-gray-100">{achievement.name}</div>
      <div className="text-xs text-gray-400">{achievement.description}</div>
      {!isLocked && (
        <div className="text-xs text-teal-400">+{achievement.xp_value} XP</div>
      )}
    </div>
  );

  return (
    <Tooltip content={tooltipContent} position="top" delay={100}>
      {badge}
    </Tooltip>
  );
}

// Skeleton loader
export function AchievementBadgeSkeleton({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const config = sizeConfig[size];

  return (
    <div
      className={cn(
        'rounded-full bg-gray-800 animate-pulse',
        config.container
      )}
    />
  );
}

export default AchievementBadge;
