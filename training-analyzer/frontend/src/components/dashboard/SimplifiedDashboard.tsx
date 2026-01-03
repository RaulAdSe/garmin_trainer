"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { ReadinessGauge } from "@/components/athlete/ReadinessGauge";
import { GamificationHeader } from "@/components/dashboard/GamificationHeader";
import { StreakCounterCompact, StreakInfo } from "@/components/gamification/StreakCounter";
import type { AthleteContext, UserProgress, FitnessMetrics } from "@/lib/types";

interface SimplifiedDashboardProps {
  context: AthleteContext;
  userProgress?: UserProgress;
  onExpandDashboard: () => void;
  className?: string;
}

/**
 * Get today's workout recommendation based on readiness.
 * Simplified version for beginner users.
 */
function getSimplifiedRecommendation(
  readinessScore: number,
  fitness: FitnessMetrics,
  t: ReturnType<typeof useTranslations>
): {
  type: string;
  duration: string;
  description: string;
  color: string;
} {
  if (readinessScore >= 75) {
    return {
      type: t("recommendations.quality"),
      duration: t("recommendations.qualityDuration"),
      description: t("recommendations.qualityDescription"),
      color: "text-green-400",
    };
  } else if (readinessScore >= 50) {
    return {
      type: t("recommendations.moderate"),
      duration: t("recommendations.moderateDuration"),
      description: t("recommendations.moderateDescription"),
      color: "text-yellow-400",
    };
  } else {
    return {
      type: t("recommendations.recovery"),
      duration: t("recommendations.recoveryDuration"),
      description: t("recommendations.recoveryDescription"),
      color: "text-red-400",
    };
  }
}

/**
 * Simplified Dashboard for beginner users.
 *
 * Shows only essential metrics:
 * - Readiness Gauge
 * - Streak Counter
 * - Next Workout suggestion
 * - Quick actions
 */
export function SimplifiedDashboard({
  context,
  userProgress,
  onExpandDashboard,
  className,
}: SimplifiedDashboardProps) {
  const t = useTranslations("simplifiedDashboard");
  const tFocus = useTranslations("focusView");

  const { score, zone, recommendation } = context.readiness;
  const workoutRec = getSimplifiedRecommendation(score, context.fitness, t);

  // Get streak info for display
  const streakInfo: StreakInfo | null = userProgress?.streak
    ? {
        current: userProgress.streak.current,
        longest: userProgress.streak.longest,
        freeze_tokens: userProgress.streak.freezeTokens,
        protected: userProgress.streak.isProtected,
      }
    : null;

  return (
    <div className={cn("space-y-4 sm:space-y-6 animate-fadeIn", className)}>
      {/* Header with beginner mode indicator */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-100">
            {t("title")}
          </h1>
          <p className="text-sm sm:text-base text-gray-400 mt-1">
            {t("subtitle")}
          </p>
        </div>
        {/* Beginner mode badge */}
        <div className="shrink-0">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-teal-500/10 border border-teal-500/30 rounded-full text-xs font-medium text-teal-400">
            <svg
              className="w-3.5 h-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
              />
            </svg>
            {t("beginnerMode")}
          </span>
        </div>
      </div>

      {/* Compact Gamification Header */}
      {userProgress && (
        <GamificationHeader userProgress={userProgress} />
      )}

      {/* Main Readiness Card - Hero Section */}
      <Card className="overflow-hidden">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2">
            <span>{t("readinessTitle")}</span>
            {/* Help tooltip */}
            <button
              className="text-gray-500 hover:text-gray-400 transition-colors"
              aria-label={t("readinessHelp")}
              title={t("readinessHelpText")}
            >
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </button>
          </CardTitle>
        </CardHeader>
        <ReadinessGauge
          score={score}
          zone={zone}
          recommendation={recommendation}
        />
      </Card>

      {/* Today's Workout Suggestion */}
      <Card className="bg-gradient-to-br from-gray-900/80 to-gray-800/80">
        <div className="p-5 sm:p-6">
          <div className="flex items-start gap-4">
            <div className="flex items-center justify-center w-12 h-12 bg-teal-500/10 rounded-xl shrink-0">
              <svg
                className="w-6 h-6 text-teal-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide">
                {t("nextWorkoutTitle")}
              </h3>
              <p className={cn("text-xl sm:text-2xl font-semibold mt-1", workoutRec.color)}>
                {workoutRec.duration} {workoutRec.type}
              </p>
              <p className="text-sm text-gray-400 mt-1">
                {workoutRec.description}
              </p>
            </div>
          </div>
        </div>
      </Card>

      {/* Streak Display (if active) */}
      {streakInfo && streakInfo.current > 0 && (
        <Card className="bg-gradient-to-r from-orange-900/20 to-amber-900/20 border-orange-500/20">
          <div className="p-4 sm:p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="text-3xl">
                  {streakInfo.current >= 7 ? (
                    <span role="img" aria-label="fire">&#128293;</span>
                  ) : (
                    <span role="img" aria-label="flame">&#128293;</span>
                  )}
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-300">
                    {t("streakTitle")}
                  </p>
                  <p className="text-2xl font-bold text-orange-400">
                    {streakInfo.current} {t("days")}
                  </p>
                </div>
              </div>
              {streakInfo.protected && (
                <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-500/10 border border-blue-500/20 rounded-full text-xs text-blue-400">
                  <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                  {t("protected")}
                </span>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-2 gap-3 sm:gap-4">
        <Link
          href="/workouts"
          className={cn(
            "flex flex-col items-center gap-2 p-4 rounded-xl",
            "bg-gray-800 hover:bg-gray-700/80 border border-gray-700",
            "transition-all duration-200 hover:border-gray-600"
          )}
        >
          <svg
            className="w-6 h-6 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
            />
          </svg>
          <span className="text-sm font-medium text-gray-300">
            {t("viewWorkouts")}
          </span>
        </Link>

        <Link
          href="/achievements"
          className={cn(
            "flex flex-col items-center gap-2 p-4 rounded-xl",
            "bg-gray-800 hover:bg-gray-700/80 border border-gray-700",
            "transition-all duration-200 hover:border-gray-600"
          )}
        >
          <svg
            className="w-6 h-6 text-purple-400"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M5 2a1 1 0 011 1v1h1a1 1 0 010 2H6v1a1 1 0 01-2 0V6H3a1 1 0 010-2h1V3a1 1 0 011-1zm0 10a1 1 0 011 1v1h1a1 1 0 110 2H6v1a1 1 0 11-2 0v-1H3a1 1 0 110-2h1v-1a1 1 0 011-1zM12 2a1 1 0 01.967.744L14.146 7.2 17.5 9.134a1 1 0 010 1.732l-3.354 1.935-1.18 4.455a1 1 0 01-1.933 0L9.854 12.8 6.5 10.866a1 1 0 010-1.732l3.354-1.935 1.18-4.455A1 1 0 0112 2z"
              clipRule="evenodd"
            />
          </svg>
          <span className="text-sm font-medium text-gray-300">
            {t("viewAchievements")}
          </span>
        </Link>
      </div>

      {/* View Full Dashboard Button */}
      <button
        onClick={onExpandDashboard}
        className={cn(
          "w-full py-3 px-4 rounded-lg",
          "bg-gray-800 hover:bg-gray-700",
          "border border-gray-700 hover:border-gray-600",
          "text-gray-300 hover:text-gray-100",
          "font-medium text-sm",
          "transition-all duration-200",
          "flex items-center justify-center gap-2"
        )}
      >
        <svg
          className="w-4 h-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
          />
        </svg>
        {t("viewFullDashboard")}
      </button>

      {/* Learn More Link */}
      <div className="text-center">
        <Link
          href="/settings"
          className="text-xs text-gray-500 hover:text-gray-400 transition-colors"
        >
          {t("disableBeginnerMode")}
        </Link>
      </div>
    </div>
  );
}

/**
 * Skeleton loader for SimplifiedDashboard.
 */
export function SimplifiedDashboardSkeleton() {
  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header skeleton */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="h-7 w-48 bg-gray-800 rounded animate-pulse" />
          <div className="h-5 w-64 bg-gray-800 rounded mt-2 animate-pulse" />
        </div>
        <div className="h-7 w-24 bg-gray-800 rounded-full animate-pulse" />
      </div>

      {/* Gamification header skeleton */}
      <div className="h-14 bg-gray-800 rounded-xl animate-pulse" />

      {/* Readiness card skeleton */}
      <div className="h-64 bg-gray-800 rounded-xl animate-pulse" />

      {/* Workout suggestion skeleton */}
      <div className="h-28 bg-gray-800 rounded-xl animate-pulse" />

      {/* Quick actions skeleton */}
      <div className="grid grid-cols-2 gap-3">
        <div className="h-24 bg-gray-800 rounded-xl animate-pulse" />
        <div className="h-24 bg-gray-800 rounded-xl animate-pulse" />
      </div>

      {/* Button skeleton */}
      <div className="h-12 bg-gray-800 rounded-lg animate-pulse" />
    </div>
  );
}

export default SimplifiedDashboard;
