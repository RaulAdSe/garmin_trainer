"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useAchievements, useUserProgress } from "@/hooks/useAchievements";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { LevelRewards, LevelRewardsCompact } from "@/components/gamification/LevelRewards";
import { LevelBadge } from "@/components/gamification/LevelBadge";
import {
  RARITY_COLORS,
  RARITY_BG_COLORS,
  type AchievementCategory,
  type AchievementWithStatus,
} from "@/lib/types";
import { clsx } from "clsx";

type CategoryFilter = AchievementCategory | "all";

export default function AchievementsPage() {
  const t = useTranslations("achievements");
  const [activeCategory, setActiveCategory] = useState<CategoryFilter>("all");

  const {
    data: achievements,
    isLoading: achievementsLoading,
    error: achievementsError,
    refetch,
  } = useAchievements();
  const { data: userProgress, isLoading: progressLoading } = useUserProgress();

  const isLoading = achievementsLoading || progressLoading;

  if (isLoading) {
    return (
      <div className="space-y-6">
        {/* Header skeleton */}
        <div>
          <div className="h-8 w-48 skeleton rounded mb-2" />
          <div className="h-5 w-64 skeleton rounded" />
        </div>

        {/* Stats skeleton */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>

        {/* Achievements grid skeleton */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  if (achievementsError) {
    return (
      <div className="py-8">
        <ErrorState
          title="Failed to load achievements"
          message={achievementsError.message}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  const categories: CategoryFilter[] = [
    "all",
    "consistency",
    "performance",
    "execution",
    "milestone",
  ];

  const filteredAchievements = achievements?.filter(
    (a) => activeCategory === "all" || a.achievement.category === activeCategory
  );

  const unlockedAchievements = filteredAchievements?.filter((a) => a.unlocked) ?? [];
  const lockedAchievements = filteredAchievements?.filter((a) => !a.unlocked) ?? [];

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="animate-fadeIn">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-100">
          {t("title")}
        </h1>
        <p className="text-sm sm:text-base text-gray-400 mt-1">
          {t("subtitle")}
        </p>
      </div>

      {/* Progress Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 animate-slideUp">
        {/* Level with Title */}
        <Card className="text-center">
          <div className="flex flex-col items-center py-2">
            <LevelBadge
              level={userProgress?.level.level ?? 1}
              size="lg"
              title={userProgress?.title}
            />
            <span className="text-sm text-gray-400 mt-2">{t("level")}</span>
            {userProgress?.title && (
              <span className="text-xs text-teal-400 font-medium">
                {userProgress.title}
              </span>
            )}
          </div>
        </Card>

        {/* Total XP with Next Reward Progress */}
        <Card className="text-center">
          <div className="flex flex-col items-center py-2">
            <span className="text-2xl sm:text-3xl font-bold text-amber-400">
              {userProgress?.totalXp?.toLocaleString() ?? 0}
            </span>
            <span className="text-sm text-gray-400">{t("totalXp")}</span>
            <div className="w-full mt-2 h-1.5 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-teal-500 to-teal-400"
                style={{ width: `${userProgress?.level.progressPercent ?? 0}%` }}
              />
            </div>
            <span className="text-xs text-gray-500 mt-1">
              {userProgress?.level.xpForNext ?? 0} XP {t("toNextLevel")}
            </span>
          </div>
        </Card>

        {/* Current Streak */}
        <Card className="text-center">
          <div className="flex flex-col items-center py-2">
            <div className="flex items-center gap-1">
              <svg className="w-6 h-6 text-orange-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M12.395 2.553a1 1 0 00-1.45-.385c-.345.23-.614.558-.822.88-.214.33-.403.713-.57 1.116-.334.804-.614 1.768-.84 2.734a31.365 31.365 0 00-.613 3.58 2.64 2.64 0 01-.945-1.067c-.328-.68-.398-1.534-.398-2.654A1 1 0 005.05 6.05 6.981 6.981 0 003 11a7 7 0 1011.95-4.95c-.592-.591-.98-.985-1.348-1.467-.363-.476-.724-1.063-1.207-2.03zM12.12 15.12A3 3 0 017 13s.879.5 2.5.5c0-1 .5-4 1.25-4.5.5 1 .786 1.293 1.371 1.879A2.99 2.99 0 0113 13a2.99 2.99 0 01-.879 2.121z" clipRule="evenodd" />
              </svg>
              <span className="text-2xl sm:text-3xl font-bold text-orange-400">
                {userProgress?.streak.current ?? 0}
              </span>
            </div>
            <span className="text-sm text-gray-400">{t("currentStreak")}</span>
          </div>
        </Card>

        {/* Longest Streak */}
        <Card className="text-center">
          <div className="flex flex-col items-center py-2">
            <span className="text-2xl sm:text-3xl font-bold text-purple-400">
              {userProgress?.streak.longest ?? 0}
            </span>
            <span className="text-sm text-gray-400">{t("longestStreak")}</span>
            <span className="text-xs text-gray-500 mt-1">{t("days")}</span>
          </div>
        </Card>
      </div>

      {/* Level Rewards Roadmap */}
      <Card className="animate-slideUp" style={{ animationDelay: "0.05s" }}>
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-gray-200 flex items-center gap-2">
            <span className="text-xl">🎁</span>
            {t("levelRewards.title")}
          </CardTitle>
        </CardHeader>
        <div className="px-4 pb-4">
          <LevelRewards
            currentLevel={userProgress?.level.level ?? 1}
            nextReward={userProgress?.nextReward}
            unlockedFeatures={userProgress?.unlockedFeatures}
          />
        </div>
      </Card>

      {/* Category Tabs */}
      <div className="flex flex-wrap gap-2 animate-slideUp" style={{ animationDelay: "0.1s" }}>
        {categories.map((category) => (
          <button
            key={category}
            onClick={() => setActiveCategory(category)}
            className={clsx(
              "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
              activeCategory === category
                ? "bg-teal-600 text-white"
                : "bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200"
            )}
          >
            {t(`categories.${category}`)}
          </button>
        ))}
      </div>

      {/* Achievements Grid */}
      {(!achievements || achievements.length === 0) ? (
        <Card className="text-center py-12 animate-slideUp" style={{ animationDelay: "0.2s" }}>
          <div className="text-6xl mb-4">🏆</div>
          <h3 className="text-lg font-medium text-gray-300 mb-2">
            {t("noAchievements")}
          </h3>
          <p className="text-sm text-gray-500">
            {t("keepTraining")}
          </p>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Unlocked Achievements */}
          {unlockedAchievements.length > 0 && (
            <div className="animate-slideUp" style={{ animationDelay: "0.2s" }}>
              <h2 className="text-lg font-semibold text-gray-200 mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-teal-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                {t("unlocked")} ({unlockedAchievements.length})
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {unlockedAchievements.map((a) => (
                  <AchievementCard key={a.achievement.id} achievement={a} t={t} />
                ))}
              </div>
            </div>
          )}

          {/* Locked Achievements */}
          {lockedAchievements.length > 0 && (
            <div className="animate-slideUp" style={{ animationDelay: "0.3s" }}>
              <h2 className="text-lg font-semibold text-gray-400 mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-gray-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                </svg>
                {t("locked")} ({lockedAchievements.length})
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {lockedAchievements.map((a) => (
                  <AchievementCard key={a.achievement.id} achievement={a} t={t} locked />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface AchievementCardProps {
  achievement: AchievementWithStatus;
  t: ReturnType<typeof useTranslations<"achievements">>;
  locked?: boolean;
}

function AchievementCard({ achievement: achWithStatus, t, locked = false }: AchievementCardProps) {
  const { achievement } = achWithStatus;
  const rarityColor = RARITY_COLORS[achievement.rarity];
  const rarityBg = RARITY_BG_COLORS[achievement.rarity];

  return (
    <Card
      className={clsx(
        "relative overflow-hidden transition-all duration-300",
        locked
          ? "opacity-60 grayscale hover:opacity-80 hover:grayscale-0"
          : "hover:scale-[1.02] hover:shadow-lg"
      )}
    >
      {/* Rarity indicator */}
      <div
        className={clsx(
          "absolute top-0 right-0 px-2 py-1 text-xs font-medium rounded-bl-lg",
          rarityBg,
          rarityColor
        )}
      >
        {t(`rarity.${achievement.rarity}`)}
      </div>

      <div className="flex items-start gap-4">
        {/* Icon */}
        <div
          className={clsx(
            "w-14 h-14 sm:w-16 sm:h-16 rounded-xl flex items-center justify-center text-3xl shrink-0",
            locked ? "bg-gray-800" : rarityBg
          )}
        >
          {achievement.icon}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <h3 className={clsx("font-semibold text-base", locked ? "text-gray-400" : "text-gray-100")}>
            {achievement.name}
          </h3>
          <p className="text-sm text-gray-500 mt-1 line-clamp-2">
            {achievement.description}
          </p>

          {/* XP Value */}
          <div className="flex items-center gap-2 mt-2">
            <span className="text-xs font-medium text-amber-400">
              +{achievement.xpValue} XP
            </span>
            {achWithStatus.unlockedAt && (
              <span className="text-xs text-gray-500">
                {new Date(achWithStatus.unlockedAt).toLocaleDateString()}
              </span>
            )}
          </div>

          {/* Progress bar for locked achievements with progress */}
          {locked && achWithStatus.progress !== undefined && achWithStatus.progress > 0 && (
            <div className="mt-2">
              <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gray-500 transition-all duration-500"
                  style={{ width: `${achWithStatus.progress}%` }}
                />
              </div>
              <span className="text-xs text-gray-500 mt-1">
                {t("progress")}: {achWithStatus.progress}%
              </span>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
