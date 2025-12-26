"use client";

import { useAthleteContext } from "@/hooks/useAthleteContext";
import { ReadinessGauge } from "@/components/athlete/ReadinessGauge";
import { FitnessMetrics } from "@/components/athlete/FitnessMetrics";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { LoadingCenter } from "@/components/ui/LoadingSpinner";
import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonMetricGrid, SkeletonCard } from "@/components/ui/Skeleton";

export default function Dashboard() {
  const { data: context, isLoading, error, refetch } = useAthleteContext();

  if (isLoading) {
    return (
      <div className="space-y-6">
        {/* Header skeleton */}
        <div>
          <div className="h-8 w-48 skeleton rounded mb-2" />
          <div className="h-5 w-64 skeleton rounded" />
        </div>

        {/* Main Grid skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
          <SkeletonCard className="lg:col-span-2" />
          <SkeletonCard />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-8">
        <ErrorState
          title="Failed to load dashboard"
          message={error.message}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="animate-fadeIn">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-100">
          Training Dashboard
        </h1>
        <p className="text-sm sm:text-base text-gray-400 mt-1">
          Your AI-powered training companion
        </p>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Readiness Card */}
        <Card className="lg:col-span-2 animate-slideUp">
          <CardHeader>
            <CardTitle>Today&apos;s Readiness</CardTitle>
          </CardHeader>
          {context && (
            <ReadinessGauge
              score={context.readiness.score}
              zone={context.readiness.zone}
              recommendation={context.readiness.recommendation}
            />
          )}
        </Card>

        {/* Quick Stats */}
        <Card className="animate-slideUp" style={{ animationDelay: "0.1s" }}>
          <CardHeader>
            <CardTitle>Fitness Status</CardTitle>
          </CardHeader>
          {context && <FitnessMetrics fitness={context.fitness} />}
        </Card>
      </div>

      {/* Training Info Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        <Card className="animate-slideUp" style={{ animationDelay: "0.2s" }}>
          <CardHeader>
            <CardTitle>Training Paces</CardTitle>
          </CardHeader>
          {context?.training_paces && context.training_paces.length > 0 ? (
            <div className="space-y-1 sm:space-y-2">
              {context.training_paces.map((pace) => (
                <div
                  key={pace.name}
                  className="flex justify-between items-center py-2 sm:py-2.5 px-2 sm:px-3 -mx-2 sm:-mx-3 rounded-lg hover:bg-gray-800/50 transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <span className="font-medium text-gray-100 text-sm sm:text-base">
                      {pace.name}
                    </span>
                    <span className="text-gray-500 text-xs sm:text-sm ml-2 hidden sm:inline">
                      {pace.hr_zone}
                    </span>
                  </div>
                  <span className="text-teal-400 font-mono text-sm sm:text-base ml-2 shrink-0">
                    {pace.pace_formatted}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500 text-sm">
                Set a race goal to see training paces
              </p>
            </div>
          )}
        </Card>

        <Card className="animate-slideUp" style={{ animationDelay: "0.3s" }}>
          <CardHeader>
            <CardTitle>HR Zones</CardTitle>
          </CardHeader>
          {context?.hr_zones && (
            <div className="space-y-1 sm:space-y-2">
              {context.hr_zones.map((zone) => (
                <div
                  key={zone.zone}
                  className="flex justify-between items-center py-2 sm:py-2.5 px-2 sm:px-3 -mx-2 sm:-mx-3 rounded-lg hover:bg-gray-800/50 transition-colors"
                >
                  <div className="flex items-center min-w-0 flex-1">
                    <span
                      className={`font-medium text-sm sm:text-base ${getZoneColor(zone.zone)}`}
                    >
                      Z{zone.zone}
                    </span>
                    <span className="text-gray-400 text-xs sm:text-sm ml-2 truncate">
                      {zone.name}
                    </span>
                  </div>
                  <span className="font-mono text-gray-300 text-xs sm:text-sm ml-2 shrink-0">
                    {zone.min_hr}-{zone.max_hr} <span className="hidden sm:inline">bpm</span>
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Race Goals */}
      {context?.race_goals && context.race_goals.length > 0 && (
        <Card className="animate-slideUp" style={{ animationDelay: "0.4s" }}>
          <CardHeader>
            <CardTitle>Race Goals</CardTitle>
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
                    <span className="text-gray-500">Race date:</span>
                    <span className="text-gray-300">{goal.race_date}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Weeks left:</span>
                    <span className="text-yellow-400 font-medium">{goal.weeks_remaining}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function getZoneColor(zone: number): string {
  const colors: Record<number, string> = {
    1: "text-blue-400",
    2: "text-green-400",
    3: "text-yellow-400",
    4: "text-orange-400",
    5: "text-red-400",
  };
  return colors[zone] || "text-gray-400";
}
