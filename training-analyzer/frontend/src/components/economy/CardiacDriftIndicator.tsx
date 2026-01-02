"use client";

import { clsx } from "clsx";
import { useTranslations } from "next-intl";
import { InfoTooltip } from "@/components/ui/Tooltip";
import { useCardiacDrift } from "@/hooks/useRunningEconomy";

interface CardiacDriftIndicatorProps {
  workoutId: string;
  className?: string;
  compact?: boolean;
}

export function CardiacDriftIndicator({
  workoutId,
  className,
  compact = false,
}: CardiacDriftIndicatorProps) {
  const t = useTranslations("economy");
  const { data, isLoading, error } = useCardiacDrift(workoutId);

  if (isLoading) {
    return (
      <div className={clsx("animate-pulse", className)}>
        <div className="h-4 bg-gray-800 rounded w-24" />
      </div>
    );
  }

  if (error || !data?.analysis) {
    if (compact) return null;
    return (
      <div className={clsx("text-gray-500 text-sm", className)}>
        {t("driftUnavailable")}
      </div>
    );
  }

  const analysis = data.analysis;

  // Determine severity color
  const getSeverityStyle = (severity: string) => {
    switch (severity) {
      case "none":
        return { color: "text-green-400", bg: "bg-green-900/30", border: "border-green-500/30" };
      case "minimal":
        return { color: "text-teal-400", bg: "bg-teal-900/30", border: "border-teal-500/30" };
      case "concerning":
        return { color: "text-yellow-400", bg: "bg-yellow-900/30", border: "border-yellow-500/30" };
      case "significant":
        return { color: "text-red-400", bg: "bg-red-900/30", border: "border-red-500/30" };
      default:
        return { color: "text-gray-400", bg: "bg-gray-800", border: "border-gray-700" };
    }
  };

  const style = getSeverityStyle(analysis.severity);

  // Compact version for inline display
  if (compact) {
    return (
      <div className={clsx("inline-flex items-center gap-1.5", className)}>
        <span className={clsx("text-xs font-medium", style.color)}>
          {analysis.driftPercent > 0 ? "+" : ""}{analysis.driftPercent.toFixed(1)}%
        </span>
        {analysis.isConcerning && (
          <svg className="w-3 h-3 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
        )}
      </div>
    );
  }

  // Full version
  return (
    <div className={clsx("bg-gray-900 rounded-xl p-4", className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-gray-400 text-sm">{t("cardiacDrift")}</span>
          <InfoTooltip
            content={
              <div className="w-[280px]">
                <div className="font-semibold text-white mb-1">{t("driftTooltipTitle")}</div>
                <div className="text-gray-300">{t("driftTooltipDescription")}</div>
              </div>
            }
            position="top"
          />
        </div>
        {analysis.isConcerning && (
          <span className="text-xs px-2 py-0.5 bg-yellow-900/30 text-yellow-400 rounded-full">
            {t("needsAttention")}
          </span>
        )}
      </div>

      {/* Main drift display */}
      <div className="flex items-center gap-4 mb-3">
        <div className={clsx("text-3xl font-bold font-mono", style.color)}>
          {analysis.driftPercent > 0 ? "+" : ""}{analysis.driftPercent.toFixed(1)}%
        </div>
        <div className="text-sm text-gray-400">
          ({analysis.driftBpm > 0 ? "+" : ""}{analysis.driftBpm.toFixed(1)} bpm)
        </div>
      </div>

      {/* HR comparison */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-500 mb-1">{t("firstHalf")}</div>
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-mono text-white">{analysis.firstHalfHr.toFixed(0)}</span>
            <span className="text-xs text-gray-400">bpm</span>
          </div>
          {analysis.firstHalfPace && (
            <div className="text-xs text-gray-500 mt-1">
              @ {formatPace(analysis.firstHalfPace)}
            </div>
          )}
        </div>
        <div className="bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-500 mb-1">{t("secondHalf")}</div>
          <div className="flex items-baseline gap-2">
            <span className={clsx("text-xl font-mono", style.color)}>
              {analysis.secondHalfHr.toFixed(0)}
            </span>
            <span className="text-xs text-gray-400">bpm</span>
          </div>
          {analysis.secondHalfPace && (
            <div className="text-xs text-gray-500 mt-1">
              @ {formatPace(analysis.secondHalfPace)}
            </div>
          )}
        </div>
      </div>

      {/* Severity indicator */}
      <div className={clsx("rounded-lg p-3 border", style.bg, style.border)}>
        <div className="flex items-center gap-2 mb-1">
          {analysis.severity === "none" && (
            <svg className="w-4 h-4 text-green-400" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
          )}
          {analysis.severity === "minimal" && (
            <svg className="w-4 h-4 text-teal-400" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
          )}
          {(analysis.severity === "concerning" || analysis.severity === "significant") && (
            <svg className={clsx("w-4 h-4", style.color)} fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
          )}
          <span className={clsx("text-sm font-medium capitalize", style.color)}>
            {t(`severity.${analysis.severity}`)}
          </span>
        </div>
        <p className="text-xs text-gray-300">{analysis.recommendation}</p>
      </div>
    </div>
  );
}

// Helper to format pace
function formatPace(paceSecPerKm: number): string {
  const minutes = Math.floor(paceSecPerKm / 60);
  const seconds = Math.floor(paceSecPerKm % 60);
  return `${minutes}:${seconds.toString().padStart(2, "0")}/km`;
}

export default CardiacDriftIndicator;
