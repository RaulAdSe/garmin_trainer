'use client';

import { useState, useMemo } from 'react';
import { cn } from '@/lib/utils';
import { AchievementCard, AchievementCardSkeleton } from './AchievementCard';
import type { Achievement } from './AchievementBadge';

export type AchievementCategory =
  | 'all'
  | 'milestones'
  | 'consistency'
  | 'performance'
  | 'social'
  | 'special';

interface AchievementGridProps {
  achievements: Achievement[];
  filter?: AchievementCategory;
  onAchievementClick?: (achievement: Achievement) => void;
  className?: string;
  showFilters?: boolean;
  loading?: boolean;
}

const categoryConfig: Record<AchievementCategory, { label: string; icon: string }> = {
  all: { label: 'All', icon: '\u{1F3C6}' },
  milestones: { label: 'Milestones', icon: '\u{1F3AF}' },
  consistency: { label: 'Consistency', icon: '\u{1F4C5}' },
  performance: { label: 'Performance', icon: '\u{26A1}' },
  social: { label: 'Social', icon: '\u{1F91D}' },
  special: { label: 'Special', icon: '\u{2B50}' },
};

export function AchievementGrid({
  achievements,
  filter: initialFilter = 'all',
  onAchievementClick,
  className,
  showFilters = true,
  loading = false,
}: AchievementGridProps) {
  const [activeFilter, setActiveFilter] = useState<AchievementCategory>(initialFilter);

  // Filter achievements by category
  const filteredAchievements = useMemo(() => {
    if (activeFilter === 'all') {
      return achievements;
    }
    return achievements.filter((a) => a.category === activeFilter);
  }, [achievements, activeFilter]);

  // Count achievements per category
  const categoryCounts = useMemo(() => {
    const counts: Record<AchievementCategory, { total: number; unlocked: number }> = {
      all: { total: achievements.length, unlocked: achievements.filter((a) => a.unlocked).length },
      milestones: { total: 0, unlocked: 0 },
      consistency: { total: 0, unlocked: 0 },
      performance: { total: 0, unlocked: 0 },
      social: { total: 0, unlocked: 0 },
      special: { total: 0, unlocked: 0 },
    };

    achievements.forEach((a) => {
      const cat = a.category as AchievementCategory;
      if (counts[cat]) {
        counts[cat].total++;
        if (a.unlocked) counts[cat].unlocked++;
      }
    });

    return counts;
  }, [achievements]);

  // Sort: unlocked first, then by rarity (legendary > epic > rare > common)
  const sortedAchievements = useMemo(() => {
    const rarityOrder = { legendary: 0, epic: 1, rare: 2, common: 3 };
    return [...filteredAchievements].sort((a, b) => {
      // Unlocked first
      if (a.unlocked !== b.unlocked) {
        return a.unlocked ? -1 : 1;
      }
      // Then by rarity
      return rarityOrder[a.rarity] - rarityOrder[b.rarity];
    });
  }, [filteredAchievements]);

  if (loading) {
    return (
      <div className={cn('space-y-4', className)}>
        {showFilters && (
          <div className="flex gap-2 overflow-x-auto pb-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-9 w-24 bg-gray-800 rounded-lg animate-pulse" />
            ))}
          </div>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <AchievementCardSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Category Filters */}
      {showFilters && (
        <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-gray-700">
          {(Object.keys(categoryConfig) as AchievementCategory[]).map((category) => {
            const config = categoryConfig[category];
            const counts = categoryCounts[category];
            const isActive = activeFilter === category;

            // Skip categories with no achievements (except 'all')
            if (category !== 'all' && counts.total === 0) {
              return null;
            }

            return (
              <button
                key={category}
                onClick={() => setActiveFilter(category)}
                className={cn(
                  'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium',
                  'whitespace-nowrap transition-all duration-200',
                  'border',
                  isActive
                    ? 'bg-teal-900/30 border-teal-700 text-teal-400'
                    : 'bg-gray-900 border-gray-800 text-gray-400 hover:border-gray-700 hover:text-gray-300'
                )}
              >
                <span>{config.icon}</span>
                <span>{config.label}</span>
                <span
                  className={cn(
                    'text-xs px-1.5 py-0.5 rounded',
                    isActive ? 'bg-teal-800 text-teal-300' : 'bg-gray-800 text-gray-500'
                  )}
                >
                  {counts.unlocked}/{counts.total}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {/* Summary */}
      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-400">
          Showing {sortedAchievements.length} achievement{sortedAchievements.length !== 1 ? 's' : ''}
        </span>
        <span className="text-gray-500">
          {filteredAchievements.filter((a) => !a.unlocked).length} locked
        </span>
      </div>

      {/* Achievement Grid */}
      {sortedAchievements.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-4xl mb-2">{categoryConfig[activeFilter].icon}</div>
          <h3 className="text-lg font-medium text-gray-300 mb-1">No achievements yet</h3>
          <p className="text-sm text-gray-500">
            Keep training to unlock achievements in this category!
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {sortedAchievements.map((achievement) => (
            <AchievementCard
              key={achievement.id}
              achievement={achievement}
              onClick={onAchievementClick ? () => onAchievementClick(achievement) : undefined}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Compact grid for dashboard widgets
interface AchievementGridCompactProps {
  achievements: Achievement[];
  maxVisible?: number;
  onViewAll?: () => void;
  className?: string;
}

export function AchievementGridCompact({
  achievements,
  maxVisible = 6,
  onViewAll,
  className,
}: AchievementGridCompactProps) {
  // Show only unlocked, sorted by most recent
  const recentAchievements = useMemo(() => {
    return achievements
      .filter((a) => a.unlocked)
      .sort((a, b) => {
        if (!a.unlocked_at || !b.unlocked_at) return 0;
        return new Date(b.unlocked_at).getTime() - new Date(a.unlocked_at).getTime();
      })
      .slice(0, maxVisible);
  }, [achievements, maxVisible]);

  const totalUnlocked = achievements.filter((a) => a.unlocked).length;
  const remainingCount = totalUnlocked - recentAchievements.length;

  return (
    <div className={cn('space-y-3', className)}>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {recentAchievements.map((achievement) => (
          <AchievementCard key={achievement.id} achievement={achievement} />
        ))}
      </div>

      {remainingCount > 0 && onViewAll && (
        <button
          onClick={onViewAll}
          className="w-full py-2 text-sm text-teal-400 hover:text-teal-300 transition-colors"
        >
          View {remainingCount} more achievement{remainingCount !== 1 ? 's' : ''}
        </button>
      )}
    </div>
  );
}

export default AchievementGrid;
