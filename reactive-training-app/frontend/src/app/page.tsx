"use client";

import { useAthleteContext } from "@/hooks/useAthleteContext";
import { AthleteContextSidebar } from "@/components/athlete/AthleteContextSidebar";
import { ReadinessGauge } from "@/components/athlete/ReadinessGauge";
import { FitnessMetrics } from "@/components/athlete/FitnessMetrics";
import { Card } from "@/components/ui/Card";

export default function Dashboard() {
  const { data: context, isLoading, error } = useAthleteContext();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-gray-400">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-red-400 p-4 bg-red-900/20 rounded-lg">
        Failed to load athlete data: {error.message}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Training Dashboard</h1>
        <p className="text-gray-400">Your AI-powered training companion</p>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Readiness Card */}
        <Card className="lg:col-span-2">
          <h2 className="text-lg font-semibold mb-4">Today&apos;s Readiness</h2>
          {context && (
            <ReadinessGauge
              score={context.readiness.score}
              zone={context.readiness.zone}
              recommendation={context.readiness.recommendation}
            />
          )}
        </Card>

        {/* Quick Stats */}
        <Card>
          <h2 className="text-lg font-semibold mb-4">Fitness Status</h2>
          {context && <FitnessMetrics fitness={context.fitness} />}
        </Card>
      </div>

      {/* Athlete Context Sidebar (for debugging/info) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <h2 className="text-lg font-semibold mb-4">Training Paces</h2>
          {context?.training_paces && context.training_paces.length > 0 ? (
            <div className="space-y-2">
              {context.training_paces.map((pace) => (
                <div
                  key={pace.name}
                  className="flex justify-between items-center py-2 border-b border-gray-800 last:border-0"
                >
                  <div>
                    <span className="font-medium">{pace.name}</span>
                    <span className="text-gray-500 text-sm ml-2">
                      {pace.hr_zone}
                    </span>
                  </div>
                  <span className="text-teal-400 font-mono">
                    {pace.pace_formatted}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">
              Set a race goal to see training paces
            </p>
          )}
        </Card>

        <Card>
          <h2 className="text-lg font-semibold mb-4">HR Zones</h2>
          {context?.hr_zones && (
            <div className="space-y-2">
              {context.hr_zones.map((zone) => (
                <div
                  key={zone.zone}
                  className="flex justify-between items-center py-2 border-b border-gray-800 last:border-0"
                >
                  <div>
                    <span
                      className={`font-medium ${getZoneColor(zone.zone)}`}
                    >
                      Z{zone.zone}
                    </span>
                    <span className="text-gray-400 ml-2">{zone.name}</span>
                  </div>
                  <span className="font-mono text-gray-300">
                    {zone.min_hr}-{zone.max_hr} bpm
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Race Goals */}
      {context?.race_goals && context.race_goals.length > 0 && (
        <Card>
          <h2 className="text-lg font-semibold mb-4">Race Goals</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {context.race_goals.map((goal, i) => (
              <div
                key={i}
                className="bg-gray-800 rounded-lg p-4 border border-gray-700"
              >
                <div className="text-lg font-bold text-teal-400">
                  {goal.distance}
                </div>
                <div className="text-2xl font-mono">
                  {goal.target_time_formatted}
                </div>
                <div className="text-sm text-gray-400">
                  {goal.target_pace_formatted}
                </div>
                <div className="mt-2 text-sm">
                  <span className="text-gray-500">Race date:</span>{" "}
                  {goal.race_date}
                </div>
                <div className="text-sm">
                  <span className="text-gray-500">Weeks remaining:</span>{" "}
                  <span className="text-yellow-400">{goal.weeks_remaining}</span>
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
