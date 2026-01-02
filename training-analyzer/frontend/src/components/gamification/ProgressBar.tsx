'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { LevelBadge } from './LevelBadge';
import type { LevelInfo } from '@/lib/types';

// Re-export for backwards compatibility
export type { LevelInfo };

interface ProgressBarProps {
  currentXP: number;
  levelInfo: LevelInfo;
  className?: string;
  showLevelBadge?: boolean;
  animate?: boolean;
}

export function ProgressBar({
  currentXP,
  levelInfo,
  className,
  showLevelBadge = true,
  animate = true,
}: ProgressBarProps) {
  const [animatedWidth, setAnimatedWidth] = useState(animate ? 0 : calculateProgress());

  // Calculate progress within current level
  function calculateProgress(): number {
    return Math.min(levelInfo.progressPercent, 100);
  }

  const xpToNextLevel = levelInfo.xpForNext;

  // Animate on mount
  useEffect(() => {
    if (animate) {
      const timer = setTimeout(() => {
        setAnimatedWidth(calculateProgress());
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [currentXP, levelInfo, animate]);

  return (
    <div className={cn('w-full', className)}>
      <div className="flex items-center gap-3">
        {/* Current Level Badge */}
        {showLevelBadge && (
          <LevelBadge level={levelInfo.level} size="md" />
        )}

        {/* Progress Bar Container */}
        <div className="flex-1">
          {/* Labels above bar */}
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-300">
                Level {levelInfo.level}
              </span>
            </div>
            <span className="text-xs text-gray-300">
              {xpToNextLevel.toLocaleString()} XP to Level {levelInfo.level + 1}
            </span>
          </div>

          {/* Progress Bar */}
          <div className="relative h-3 bg-gray-800 rounded-full overflow-hidden">
            {/* Animated gradient fill */}
            <div
              className={cn(
                'absolute inset-y-0 left-0 rounded-full',
                'bg-gradient-to-r from-teal-500 via-teal-400 to-green-400',
                animate && 'transition-all duration-1000 ease-out'
              )}
              style={{ width: `${animatedWidth}%` }}
            >
              {/* Shimmer effect */}
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
            </div>

            {/* XP text inside bar */}
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-[10px] font-medium text-white/80 drop-shadow-sm">
                {levelInfo.xpInLevel.toLocaleString()} / {(levelInfo.xpForNext + levelInfo.xpInLevel).toLocaleString()} XP
              </span>
            </div>
          </div>
        </div>

        {/* Next Level Badge (muted) */}
        {showLevelBadge && (
          <div className="opacity-40">
            <LevelBadge level={levelInfo.level + 1} size="sm" />
          </div>
        )}
      </div>
    </div>
  );
}

// Compact version for nav/header
interface ProgressBarCompactProps {
  currentXP: number;
  levelInfo: LevelInfo;
  className?: string;
}

export function ProgressBarCompact({
  currentXP,
  levelInfo,
  className,
}: ProgressBarCompactProps) {
  const progressPercent = Math.min(levelInfo.progressPercent, 100);

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <LevelBadge level={levelInfo.level} size="sm" />
      <div className="w-20 h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-teal-500 to-green-400 rounded-full"
          style={{ width: `${progressPercent}%` }}
        />
      </div>
    </div>
  );
}

// Skeleton loader
export function ProgressBarSkeleton() {
  return (
    <div className="w-full animate-pulse">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-gray-800" />
        <div className="flex-1">
          <div className="flex justify-between mb-1.5">
            <div className="h-4 w-24 bg-gray-800 rounded" />
            <div className="h-3 w-20 bg-gray-800 rounded" />
          </div>
          <div className="h-3 w-full bg-gray-800 rounded-full" />
        </div>
        <div className="w-8 h-8 rounded-full bg-gray-800 opacity-40" />
      </div>
    </div>
  );
}

export default ProgressBar;
