"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import type { AthleteContext } from "@/lib/types";

interface FocusViewProps {
  context: AthleteContext;
  onExpandDashboard: () => void;
}

// Get motivational message based on readiness score
function getMotivationalMessage(
  score: number,
  zone: string,
  t: ReturnType<typeof useTranslations>
): { message: string; subMessage: string } {
  if (score >= 75 || zone === "green") {
    return {
      message: t("readyForQuality"),
      subMessage: t("readyForQualityMessage"),
    };
  } else if (score >= 50 || zone === "yellow") {
    return {
      message: t("goodForSteady"),
      subMessage: t("goodForSteadyMessage"),
    };
  } else {
    return {
      message: t("focusOnRecovery"),
      subMessage: t("focusOnRecoveryMessage"),
    };
  }
}

// Get zone color configuration
function getZoneConfig(score: number, zone: string) {
  if (score >= 75 || zone === "green") {
    return {
      textColor: "text-green-400",
      bgGlow: "shadow-green-500/20",
      ringColor: "ring-green-500/30",
    };
  } else if (score >= 50 || zone === "yellow") {
    return {
      textColor: "text-yellow-400",
      bgGlow: "shadow-yellow-500/20",
      ringColor: "ring-yellow-500/30",
    };
  } else {
    return {
      textColor: "text-red-400",
      bgGlow: "shadow-red-500/20",
      ringColor: "ring-red-500/30",
    };
  }
}

// Format duration to readable string
function formatDuration(minutes: number): string {
  if (minutes < 60) {
    return `${minutes}min`;
  }
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (mins === 0) {
    return `${hours}h`;
  }
  return `${hours}h ${mins}min`;
}

// Get today's recommended training based on fitness state
function getTodaysRecommendation(
  fitness: AthleteContext["fitness"],
  readinessScore: number,
  t: ReturnType<typeof useTranslations>
): { type: string; duration: string } {
  const { tsb, acwr, risk_zone, ctl } = fitness;

  // Calculate recommended load range
  const baseLoad = ctl * 0.8;
  const highLoad = ctl * 1.3;

  // Determine workout type based on readiness and TSB
  if (readinessScore >= 75 && tsb >= 5) {
    // Ready for quality work
    if (acwr < 1.0) {
      return {
        type: t("workoutTypes.quality"),
        duration: formatDuration(60),
      };
    }
    return {
      type: t("workoutTypes.tempo"),
      duration: formatDuration(45),
    };
  } else if (readinessScore >= 50) {
    // Good for steady training
    if (risk_zone === "optimal" || risk_zone === "undertrained") {
      return {
        type: t("workoutTypes.easyRun"),
        duration: formatDuration(45),
      };
    }
    return {
      type: t("workoutTypes.moderate"),
      duration: formatDuration(40),
    };
  } else {
    // Focus on recovery
    if (tsb < -20) {
      return {
        type: t("workoutTypes.rest"),
        duration: t("workoutTypes.fullRecovery"),
      };
    }
    return {
      type: t("workoutTypes.recovery"),
      duration: formatDuration(30),
    };
  }
}

export function FocusView({ context, onExpandDashboard }: FocusViewProps) {
  const t = useTranslations("focusView");

  const { score, zone } = context.readiness;
  const zoneConfig = getZoneConfig(score, zone);
  const motivational = getMotivationalMessage(score, zone, t);
  const recommendation = getTodaysRecommendation(context.fitness, score, t);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4 animate-fadeIn">
      <div
        className={cn(
          "w-full max-w-md bg-gray-900/80 backdrop-blur-sm rounded-2xl p-8 space-y-8",
          "ring-1",
          zoneConfig.ringColor,
          "shadow-lg",
          zoneConfig.bgGlow
        )}
      >
        {/* Readiness Section */}
        <div className="text-center space-y-2">
          <p className="text-sm font-medium text-gray-400 uppercase tracking-wider">
            {t("readiness")}
          </p>
          <div
            className={cn(
              "text-7xl sm:text-8xl font-bold tabular-nums transition-colors duration-500",
              zoneConfig.textColor
            )}
          >
            {Math.round(score)}
          </div>
          <p className={cn("text-xl font-semibold", zoneConfig.textColor)}>
            {motivational.message}
          </p>
        </div>

        {/* Divider */}
        <div className="border-t border-gray-700/50" />

        {/* Today's Recommendation */}
        <div className="text-center space-y-3">
          <p className="text-sm font-medium text-gray-400 uppercase tracking-wider">
            {t("today")}
          </p>
          <div className="space-y-1">
            <p className="text-xl sm:text-2xl font-semibold text-gray-100">
              {recommendation.duration} {recommendation.type}
            </p>
            <p className="text-sm text-gray-400 italic">
              "{motivational.subMessage}"
            </p>
          </div>
        </div>

        {/* Expand Button */}
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
      </div>
    </div>
  );
}

// Skeleton loader for Focus View
export function FocusViewSkeleton() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
      <div className="w-full max-w-md bg-gray-900/80 backdrop-blur-sm rounded-2xl p-8 space-y-8 ring-1 ring-gray-700/30">
        {/* Readiness Section Skeleton */}
        <div className="text-center space-y-2">
          <div className="h-4 w-24 bg-gray-700 rounded mx-auto animate-pulse" />
          <div className="h-20 w-32 bg-gray-700 rounded mx-auto animate-pulse" />
          <div className="h-6 w-40 bg-gray-700 rounded mx-auto animate-pulse" />
        </div>

        {/* Divider */}
        <div className="border-t border-gray-700/50" />

        {/* Today's Recommendation Skeleton */}
        <div className="text-center space-y-3">
          <div className="h-4 w-16 bg-gray-700 rounded mx-auto animate-pulse" />
          <div className="space-y-2">
            <div className="h-7 w-48 bg-gray-700 rounded mx-auto animate-pulse" />
            <div className="h-4 w-56 bg-gray-700 rounded mx-auto animate-pulse" />
          </div>
        </div>

        {/* Button Skeleton */}
        <div className="h-12 w-full bg-gray-800 rounded-lg animate-pulse" />
      </div>
    </div>
  );
}
