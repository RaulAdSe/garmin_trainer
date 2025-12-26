"use client";

import { useAthleteContext } from "@/hooks/useAthleteContext";
import { ReadinessGauge } from "./ReadinessGauge";
import { FitnessMetrics } from "./FitnessMetrics";
import { Card } from "@/components/ui/Card";

export function AthleteContextSidebar() {
  const { data: context, isLoading, error } = useAthleteContext();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl animate-pulse h-32" />
        <div className="bg-gray-900 border border-gray-800 rounded-xl animate-pulse h-48" />
      </div>
    );
  }

  if (error || !context) {
    return (
      <Card className="text-red-400">
        Failed to load athlete context
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Readiness */}
      <Card>
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
          Readiness
        </h3>
        <ReadinessGauge
          score={context.readiness.score}
          zone={context.readiness.zone}
          recommendation={context.readiness.recommendation}
        />
      </Card>

      {/* Fitness */}
      <Card>
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
          Fitness Status
        </h3>
        <FitnessMetrics fitness={context.fitness} />
      </Card>

      {/* VDOT if available */}
      {context.physiology.vdot && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
            Estimated Fitness
          </h3>
          <div className="text-center">
            <div className="text-3xl font-bold text-teal-400">
              {context.physiology.vdot}
            </div>
            <div className="text-sm text-gray-400">VDOT</div>
          </div>
        </Card>
      )}

      {/* Next Goal */}
      {context.race_goals.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
            Next Goal
          </h3>
          <div className="text-center">
            <div className="text-lg font-bold text-white">
              {context.race_goals[0].distance}
            </div>
            <div className="text-2xl font-mono text-teal-400">
              {context.race_goals[0].target_time_formatted}
            </div>
            <div className="text-sm text-gray-400">
              {context.race_goals[0].target_pace_formatted}
            </div>
            <div className="mt-2 text-yellow-400 text-sm font-medium">
              {context.race_goals[0].weeks_remaining} weeks
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
