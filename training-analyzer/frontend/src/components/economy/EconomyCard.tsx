"use client";

import { clsx } from "clsx";
import { useTranslations } from "next-intl";
import { InfoTooltip } from "@/components/ui/Tooltip";
import { useCurrentEconomy } from "@/hooks/useRunningEconomy";

interface EconomyCardProps {
  className?: string;
}

export function EconomyCard({ className }: EconomyCardProps) {
  const t = useTranslations("economy");
  const { data, isLoading, error } = useCurrentEconomy();

  if (isLoading) {
    return (
      <div className={clsx("bg-gray-900 rounded-xl p-4 animate-pulse", className)}>
        <div className="h-4 bg-gray-800 rounded w-1/3 mb-3" />
        <div className="h-8 bg-gray-800 rounded w-1/2 mb-2" />
        <div className="h-3 bg-gray-800 rounded w-2/3" />
      </div>
    );
  }

  if (error || !data?.hasData) {
    return (
      <div className={clsx("bg-gray-900 rounded-xl p-4", className)}>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-gray-400 text-sm">{t("title")}</span>
          <InfoTooltip
            content={
              <div className="w-[280px]">
                <div className="font-semibold text-white mb-1">{t("tooltipTitle")}</div>
                <div className="text-gray-300">{t("tooltipDescription")}</div>
              </div>
            }
            position="top"
          />
        </div>
        <p className="text-gray-500 text-sm">{t("noData")}</p>
      </div>
    );
  }

  const metrics = data.metrics;
  if (!metrics) return null;

  // Determine color based on economy label
  const getEconomyColor = (label: string) => {
    switch (label.toLowerCase()) {
      case "personal best":
      case "excellent":
        return "text-green-400";
      case "near best":
      case "very good":
        return "text-teal-400";
      case "good":
        return "text-blue-400";
      case "average":
        return "text-yellow-400";
      default:
        return "text-orange-400";
    }
  };

  // Get trend indicator
  const getTrendInfo = () => {
    if (metrics.comparisonToBest === null || metrics.comparisonToBest === undefined) {
      return null;
    }
    const diff = metrics.comparisonToBest;
    if (Math.abs(diff) < 1) {
      return { direction: "stable", color: "text-gray-400", icon: "minus" };
    }
    if (diff < 0) {
      return { direction: "better", color: "text-green-400", icon: "up" };
    }
    return { direction: "worse", color: "text-red-400", icon: "down" };
  };

  const trend = getTrendInfo();

  return (
    <div className={clsx("bg-gray-900 rounded-xl p-4", className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-gray-400 text-sm">{t("title")}</span>
          <InfoTooltip
            content={
              <div className="w-[280px]">
                <div className="font-semibold text-white mb-1">{t("tooltipTitle")}</div>
                <div className="text-gray-300">{t("tooltipDescription")}</div>
              </div>
            }
            position="top"
          />
        </div>
        {metrics.paceZone && (
          <span className="text-xs px-2 py-0.5 bg-gray-800 rounded-full text-gray-400 capitalize">
            {metrics.paceZone}
          </span>
        )}
      </div>

      {/* Main metric */}
      <div className="flex items-baseline gap-3 mb-2">
        <span className={clsx("text-3xl font-bold font-mono", getEconomyColor(metrics.economyLabel))}>
          {metrics.economyRatio.toFixed(2)}
        </span>
        {trend && (
          <div className={clsx("flex items-center", trend.color)}>
            {trend.direction === "better" && (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
              </svg>
            )}
            {trend.direction === "worse" && (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
              </svg>
            )}
            {trend.direction === "stable" && (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14" />
              </svg>
            )}
            <span className="text-xs ml-0.5">
              {metrics.comparisonToBest !== null && Math.abs(metrics.comparisonToBest).toFixed(1)}%
            </span>
          </div>
        )}
      </div>

      {/* Label */}
      <div className={clsx("text-sm font-medium mb-3", getEconomyColor(metrics.economyLabel))}>
        {metrics.economyLabel}
      </div>

      {/* Details */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="bg-gray-800 rounded-lg p-2">
          <div className="text-gray-500 text-xs">{t("pace")}</div>
          <div className="text-white font-mono">{metrics.paceFormatted}</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-2">
          <div className="text-gray-500 text-xs">{t("avgHr")}</div>
          <div className="text-white font-mono">{metrics.avgHr} bpm</div>
        </div>
      </div>

      {/* Best economy comparison */}
      {metrics.bestEconomy && (
        <div className="mt-3 pt-3 border-t border-gray-800">
          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-500">{t("bestEconomy")}</span>
            <span className="text-green-400 font-mono">{metrics.bestEconomy.toFixed(2)}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default EconomyCard;
