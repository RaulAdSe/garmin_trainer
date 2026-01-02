"use client";

import { clsx } from "clsx";
import { useTranslations } from "next-intl";
import { useMemo } from "react";
import { useEconomyTrend } from "@/hooks/useRunningEconomy";

interface EconomyDataPoint {
  date: string;
  economyRatio: number;
  pace: string;
  avgHr: number;
  workoutId: string;
}

interface EconomyTrendChartProps {
  days?: number;
  className?: string;
}

export function EconomyTrendChart({ days = 90, className }: EconomyTrendChartProps) {
  const t = useTranslations("economy");
  const { data, isLoading, error } = useEconomyTrend(days);

  // Process data for chart
  const chartData = useMemo(() => {
    if (!data?.trend?.dataPoints || data.trend.dataPoints.length === 0) {
      return null;
    }

    const points: EconomyDataPoint[] = data.trend.dataPoints;
    const values = points.map((p: EconomyDataPoint) => p.economyRatio);
    const minVal = Math.min(...values);
    const maxVal = Math.max(...values);
    const range = maxVal - minVal || 0.1;

    // Normalize values to 0-100 range for chart
    // Note: For economy, lower is better, so we invert
    const normalizedPoints = points.map((p: EconomyDataPoint) => ({
      ...p,
      normalized: 100 - ((p.economyRatio - minVal) / range) * 100,
    }));

    return {
      points: normalizedPoints,
      minVal,
      maxVal,
      range,
    };
  }, [data]);

  if (isLoading) {
    return (
      <div className={clsx("bg-gray-900 rounded-xl p-4 animate-pulse", className)}>
        <div className="h-4 bg-gray-800 rounded w-1/3 mb-4" />
        <div className="h-32 bg-gray-800 rounded" />
      </div>
    );
  }

  if (error || !data?.trend || data.trend.workoutCount === 0) {
    return (
      <div className={clsx("bg-gray-900 rounded-xl p-4", className)}>
        <h3 className="text-gray-400 text-sm mb-2">{t("trendTitle")}</h3>
        <p className="text-gray-500 text-sm">{t("noTrendData")}</p>
      </div>
    );
  }

  const trend = data.trend;

  // Get trend color and icon
  const getTrendStyle = (direction: string) => {
    switch (direction) {
      case "improving":
        return { color: "text-green-400", bg: "bg-green-900/30" };
      case "declining":
        return { color: "text-red-400", bg: "bg-red-900/30" };
      default:
        return { color: "text-gray-400", bg: "bg-gray-800" };
    }
  };

  const trendStyle = getTrendStyle(trend.trendDirection);

  return (
    <div className={clsx("bg-gray-900 rounded-xl p-4", className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-gray-300 text-sm font-medium">{t("trendTitle")}</h3>
        <div className={clsx("px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1", trendStyle.bg, trendStyle.color)}>
          {trend.trendDirection === "improving" && (
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
            </svg>
          )}
          {trend.trendDirection === "declining" && (
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          )}
          {trend.trendDirection === "stable" && (
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14" />
            </svg>
          )}
          {trend.improvementPercent > 0 ? "+" : ""}{trend.improvementPercent.toFixed(1)}%
        </div>
      </div>

      {/* Chart */}
      {chartData && chartData.points.length > 1 && (
        <div className="relative h-32 mb-4">
          {/* Y-axis labels */}
          <div className="absolute left-0 top-0 bottom-0 w-10 flex flex-col justify-between text-xs text-gray-500 font-mono pr-2">
            <span>{chartData.minVal.toFixed(2)}</span>
            <span>{chartData.maxVal.toFixed(2)}</span>
          </div>

          {/* Chart area */}
          <div className="ml-12 h-full relative">
            <svg className="w-full h-full" preserveAspectRatio="none">
              {/* Grid lines */}
              <line x1="0" y1="50%" x2="100%" y2="50%" stroke="#374151" strokeWidth="1" strokeDasharray="4" />

              {/* Line chart */}
              <polyline
                fill="none"
                stroke="#14b8a6"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={chartData.points
                  .map((p, i) => {
                    const x = (i / (chartData.points.length - 1)) * 100;
                    const y = 100 - p.normalized;
                    return `${x}%,${y}%`;
                  })
                  .join(" ")}
              />

              {/* Data points */}
              {chartData.points.map((p, i) => {
                const x = (i / (chartData.points.length - 1)) * 100;
                const y = 100 - p.normalized;
                return (
                  <circle
                    key={i}
                    cx={`${x}%`}
                    cy={`${y}%`}
                    r="3"
                    fill="#14b8a6"
                    className="hover:r-4 transition-all"
                  />
                );
              })}
            </svg>

            {/* Best marker */}
            {trend.bestEconomyDate && (
              <div className="absolute bottom-0 left-0 right-0 flex justify-center">
                <span className="text-xs text-green-400">
                  {t("bestOnDate", { date: trend.bestEconomyDate })}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2 text-sm">
        <div className="bg-gray-800 rounded-lg p-2 text-center">
          <div className="text-gray-500 text-xs">{t("current")}</div>
          <div className="text-white font-mono">{trend.currentEconomy.toFixed(2)}</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-2 text-center">
          <div className="text-gray-500 text-xs">{t("best")}</div>
          <div className="text-green-400 font-mono">{trend.bestEconomy.toFixed(2)}</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-2 text-center">
          <div className="text-gray-500 text-xs">{t("average")}</div>
          <div className="text-gray-300 font-mono">{trend.avgEconomy.toFixed(2)}</div>
        </div>
      </div>

      {/* Workouts count */}
      <div className="mt-3 text-center text-xs text-gray-500">
        {t("basedOnWorkouts", { count: trend.workoutCount })}
      </div>
    </div>
  );
}

export default EconomyTrendChart;
