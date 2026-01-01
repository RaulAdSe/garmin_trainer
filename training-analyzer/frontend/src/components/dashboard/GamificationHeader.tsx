"use client";

import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import { LevelBadge } from "@/components/gamification/LevelBadge";
import { StreakCounterCompact, StreakInfo } from "@/components/gamification/StreakCounter";
import type { UserProgress } from "@/lib/types";

interface GamificationHeaderProps {
  userProgress: UserProgress | undefined;
  className?: string;
}

export function GamificationHeader({ userProgress, className }: GamificationHeaderProps) {
  const level = userProgress?.level?.level ?? 1;
  const streak = userProgress?.streak;
  const achievementsCount = userProgress?.achievementsUnlocked ?? 0;
  const xpProgress = userProgress?.level?.progressPercent ?? 0;

  // Convert streak format if needed
  const streakInfo: StreakInfo | null = streak
    ? {
        current: streak.current,
        longest: streak.longest,
        freeze_tokens: streak.freezeTokens,
        protected: streak.isProtected,
      }
    : null;

  return (
    <div
      className={cn(
        "flex items-center justify-between gap-4 px-4 py-3",
        "bg-gradient-to-r from-gray-900/80 to-gray-800/80",
        "border border-gray-800 rounded-xl",
        "animate-fadeIn",
        className
      )}
    >
      {/* Left: Level + XP Progress */}
      <div className="flex items-center gap-3">
        <LevelBadge level={level} size="sm" />
        <div className="flex flex-col">
          <span className="text-sm font-medium text-gray-300">
            Level {level}
          </span>
          {/* Compact XP bar */}
          <div className="w-20 h-1.5 bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-teal-500 to-teal-400 rounded-full transition-all duration-500"
              style={{ width: `${xpProgress}%` }}
            />
          </div>
        </div>
      </div>

      {/* Center: Streak */}
      {streakInfo && (
        <StreakCounterCompact streakInfo={streakInfo} />
      )}

      {/* Right: Achievements */}
      <Link
        href="/achievements"
        className={cn(
          "flex items-center gap-2 px-3 py-1.5 rounded-lg",
          "bg-purple-500/10 border border-purple-500/20",
          "hover:bg-purple-500/20 transition-colors"
        )}
      >
        <svg
          className="w-4 h-4 text-purple-400"
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path
            fillRule="evenodd"
            d="M5 2a1 1 0 011 1v1h1a1 1 0 010 2H6v1a1 1 0 01-2 0V6H3a1 1 0 010-2h1V3a1 1 0 011-1zm0 10a1 1 0 011 1v1h1a1 1 0 110 2H6v1a1 1 0 11-2 0v-1H3a1 1 0 110-2h1v-1a1 1 0 011-1zM12 2a1 1 0 01.967.744L14.146 7.2 17.5 9.134a1 1 0 010 1.732l-3.354 1.935-1.18 4.455a1 1 0 01-1.933 0L9.854 12.8 6.5 10.866a1 1 0 010-1.732l3.354-1.935 1.18-4.455A1 1 0 0112 2z"
            clipRule="evenodd"
          />
        </svg>
        <span className="text-sm font-bold text-purple-400">
          {achievementsCount}
        </span>
      </Link>
    </div>
  );
}

// Skeleton loader
export function GamificationHeaderSkeleton() {
  return (
    <div className="flex items-center justify-between gap-4 px-4 py-3 bg-gray-900/80 border border-gray-800 rounded-xl animate-pulse">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-gray-800" />
        <div className="space-y-1">
          <div className="w-16 h-4 bg-gray-800 rounded" />
          <div className="w-20 h-1.5 bg-gray-800 rounded-full" />
        </div>
      </div>
      <div className="w-16 h-8 bg-gray-800 rounded" />
      <div className="w-16 h-8 bg-gray-800 rounded-lg" />
    </div>
  );
}
