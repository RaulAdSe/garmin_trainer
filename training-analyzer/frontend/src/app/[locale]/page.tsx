"use client";

import { useEffect, useMemo } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { Link } from "@/i18n/navigation";
import { useAthleteContext, useVO2MaxTrend } from "@/hooks/useAthleteContext";
import { useUserProgress, useAchievements } from "@/hooks/useAchievements";
import { useDataFreshness } from "@/hooks/useDataFreshness";
import { useWorkouts } from "@/hooks/useWorkouts";
import { useAuth } from "@/contexts/auth-context";
import { hasAuthToken } from "@/lib/auth-fetch";
import { ReadinessGauge } from "@/components/athlete/ReadinessGauge";
import { VO2MaxCard } from "@/components/athlete/VO2MaxCard";
import {
  GamificationHeader,
  GamificationHeaderSkeleton,
  TodaysTraining,
  TodaysTrainingSkeleton,
  TrainingBalance,
  TrainingBalanceSkeleton,
  FocusView,
  FocusViewSkeleton,
  DashboardToggle,
  useDashboardViewMode,
} from "@/components/dashboard";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { DataFreshnessIndicator } from "@/components/ui/DataFreshnessIndicator";
import { TooltipTriggers } from "@/components/onboarding";

export default function Dashboard() {
  const t = useTranslations("dashboard");
  const tVO2Max = useTranslations("vo2max");
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { data: context, isLoading, error, refetch } = useAthleteContext();
  const { data: userProgress, isLoading: progressLoading } = useUserProgress();
  const { data: vo2maxData, isLoading: vo2maxLoading } = useVO2MaxTrend(90);
  const { data: achievements } = useAchievements();
  const { total: workoutCount } = useWorkouts({ pageSize: 1 });
  const dataFreshness = useDataFreshness({ staleThresholdHours: 72 });
  const [viewMode, setViewMode, isViewModeLoaded] = useDashboardViewMode();

  // Compute onboarding tooltip data
  const achievementCount = useMemo(
    () => achievements?.filter((a) => a.unlockedAt).length ?? 0,
    [achievements]
  );
  const currentLevel = typeof userProgress?.level === 'number' ? userProgress.level : 1;

  // Check if error is a 401 and redirect to login
  const is401Error = error && (
    (error as { status?: number }).status === 401 ||
    error.message?.includes('401') ||
    error.message?.toLowerCase().includes('unauthorized')
  );

  useEffect(() => {
    if (is401Error) {
      router.push('/login');
    }
  }, [is401Error, router]);

  // Show loading state while auth or view mode is being checked
  if (authLoading || !isViewModeLoaded) {
    return (
      <div className="space-y-4 sm:space-y-6">
        <div>
          <div className="h-8 w-48 skeleton rounded mb-2" />
          <div className="h-5 w-64 skeleton rounded" />
        </div>
        <GamificationHeaderSkeleton />
        <SkeletonCard className="h-64" />
      </div>
    );
  }

  // If not authenticated AND no token present, show login prompt
  // (hasAuthToken is a fallback for when /api/v1/auth/me fails but token exists)
  if (!isAuthenticated && !hasAuthToken()) {
    return (
      <div className="py-8">
        <Card className="max-w-md mx-auto">
          <div className="p-6 text-center space-y-4">
            <svg
              className="w-16 h-16 mx-auto text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
              />
            </svg>
            <h2 className="text-xl font-semibold text-gray-100">
              {t("loginRequired")}
            </h2>
            <p className="text-gray-400">
              {t("loginRequiredMessage")}
            </p>
            <Link
              href="/login"
              className="inline-flex items-center justify-center px-6 py-2 bg-teal-600 hover:bg-teal-500 text-white font-medium rounded-lg transition-colors"
            >
              {t("goToLogin")}
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  if (isLoading) {
    // Show appropriate skeleton based on view mode
    if (viewMode === "focus") {
      return <FocusViewSkeleton />;
    }

    return (
      <div className="space-y-4 sm:space-y-6">
        {/* Header skeleton */}
        <div>
          <div className="h-8 w-48 skeleton rounded mb-2" />
          <div className="h-5 w-64 skeleton rounded" />
        </div>

        {/* Gamification header skeleton */}
        <GamificationHeaderSkeleton />

        {/* Readiness hero skeleton */}
        <SkeletonCard className="h-64" />

        {/* 2-column grid skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
          <SkeletonCard />
          <SkeletonCard />
        </div>

        {/* Training balance skeleton */}
        <TrainingBalanceSkeleton />
      </div>
    );
  }

  // If it's a 401 error, we're redirecting - show loading state
  if (is401Error) {
    return (
      <div className="space-y-4 sm:space-y-6">
        <div>
          <div className="h-8 w-48 skeleton rounded mb-2" />
          <div className="h-5 w-64 skeleton rounded" />
        </div>
        <GamificationHeaderSkeleton />
        <SkeletonCard className="h-64" />
      </div>
    );
  }

  // Show error state for non-401 errors
  if (error) {
    return (
      <div className="py-8">
        <ErrorState
          title={t("failedToLoad")}
          message={error.message}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  // Render Focus View when in focus mode
  if (viewMode === "focus" && context) {
    return (
      <div className="space-y-4 sm:space-y-6">
        {/* Header with toggle */}
        <div className="flex items-center justify-between animate-fadeIn">
          <div className="flex items-center gap-4">
            <h1 className="text-xl sm:text-2xl font-bold text-gray-100">
              {t("title")}
            </h1>
          </div>
          <DashboardToggle
            viewMode={viewMode}
            onViewModeChange={setViewMode}
          />
        </div>

        {/* Focus View */}
        <FocusView
          context={context}
          onExpandDashboard={() => setViewMode("full")}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="animate-fadeIn">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-gray-100">
              {t("title")}
            </h1>
            <p className="text-sm sm:text-base text-gray-400 mt-1">
              {t("subtitle")}
            </p>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            {/* Dashboard View Toggle */}
            <DashboardToggle
              viewMode={viewMode}
              onViewModeChange={setViewMode}
            />
            {/* Data Freshness Indicator */}
            {!dataFreshness.isLoading && (
              <DataFreshnessIndicator
                lastSyncTime={dataFreshness.lastSyncTime}
                relativeTimeString={dataFreshness.relativeTimeString}
                onRefresh={dataFreshness.refresh}
                isRefreshing={dataFreshness.isSyncing}
                canRefresh={dataFreshness.hasCredentials}
                staleThresholdHours={72}
              />
            )}
          </div>
        </div>
      </div>

      {/* Compact Gamification Header */}
      <div data-onboarding="level-badge">
        <GamificationHeader userProgress={userProgress} />
      </div>

      {/* Readiness Hero - Full Width */}
      <Card className="animate-slideUp" data-onboarding="readiness-gauge">
        <CardHeader>
          <CardTitle>{t("readinessCard")}</CardTitle>
        </CardHeader>
        {context && (
          <ReadinessGauge
            score={context.readiness.score}
            zone={context.readiness.zone}
            recommendation={context.readiness.recommendation}
          />
        )}
      </Card>

      {/* 2-Column Grid: Fitness Status + Today's Training */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* VO2Max / Fitness Status */}
        <Card className="animate-slideUp" style={{ animationDelay: "0.05s" }}>
          <CardHeader>
            <CardTitle>{tVO2Max("cardTitle")}</CardTitle>
          </CardHeader>
          <VO2MaxCard vo2maxData={vo2maxData} isLoading={vo2maxLoading} />
        </Card>

        {/* Today's Training */}
        <Card className="animate-slideUp" style={{ animationDelay: "0.1s" }}>
          <CardHeader>
            <CardTitle>{t("todaysTraining")}</CardTitle>
          </CardHeader>
          {context ? (
            <TodaysTraining fitness={context.fitness} />
          ) : (
            <TodaysTrainingSkeleton />
          )}
        </Card>
      </div>

      {/* Training Balance - Full Width */}
      {context && (
        <TrainingBalance
          ctl={context.fitness.ctl}
          atl={context.fitness.atl}
          className="animate-slideUp"
          style={{ animationDelay: "0.15s" }}
        />
      )}

      {/* Quick Action Links */}
      <div className="flex flex-wrap gap-3 animate-slideUp" style={{ animationDelay: "0.2s" }}>
        <Link
          href="/workouts"
          className="inline-flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-sm text-gray-300 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          {t("viewWorkouts")}
        </Link>
        <Link
          href="/achievements"
          className="inline-flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-sm text-gray-300 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
          {t("viewProgress")}
        </Link>
        <Link
          href="/goals"
          className="inline-flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-sm text-gray-300 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {t("viewGoals")}
        </Link>
      </div>

      {/* Race Goals - Conditional */}
      {context?.race_goals && context.race_goals.length > 0 && (
        <Card className="animate-slideUp" style={{ animationDelay: "0.25s" }}>
          <CardHeader>
            <CardTitle>{t("raceGoals")}</CardTitle>
          </CardHeader>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
            {context.race_goals.map((goal, i) => (
              <div
                key={i}
                className="bg-gray-800 rounded-lg p-3 sm:p-4 border border-gray-700 hover:border-gray-600 transition-colors"
              >
                <div className="text-base sm:text-lg font-bold text-teal-400">
                  {goal.distance}
                </div>
                <div className="text-xl sm:text-2xl font-mono text-gray-100">
                  {goal.target_time_formatted}
                </div>
                <div className="text-xs sm:text-sm text-gray-400">
                  {goal.target_pace_formatted}
                </div>
                <div className="mt-2 sm:mt-3 pt-2 sm:pt-3 border-t border-gray-700 text-xs sm:text-sm space-y-1">
                  <div className="flex justify-between">
                    <span className="text-gray-500">{t("raceDate")}</span>
                    <span className="text-gray-300">{goal.race_date}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">{t("weeksLeft")}</span>
                    <span className="text-yellow-400 font-medium">{goal.weeks_remaining}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Contextual Onboarding Tooltips */}
      <TooltipTriggers
        hasNoWorkouts={workoutCount === 0}
        workoutCount={workoutCount}
        currentLevel={currentLevel}
        achievementCount={achievementCount}
      />
    </div>
  );
}
