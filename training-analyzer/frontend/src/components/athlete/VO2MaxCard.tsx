"use client";

import { clsx } from "clsx";
import { useTranslations } from "next-intl";
import { InfoTooltip } from "@/components/ui/Tooltip";
import type { VO2MaxTrend } from "@/lib/types";

interface VO2MaxCardProps {
  vo2maxData: VO2MaxTrend | null | undefined;
  isLoading?: boolean;
}

// Training status configurations from Garmin
const TRAINING_STATUS_CONFIG: Record<string, { label: string; color: string; bgColor: string; icon: string }> = {
  productive: { label: "Productive", color: "text-green-400", bgColor: "bg-green-500/20", icon: "📈" },
  maintaining: { label: "Maintaining", color: "text-blue-400", bgColor: "bg-blue-500/20", icon: "➡️" },
  recovery: { label: "Recovery", color: "text-cyan-400", bgColor: "bg-cyan-500/20", icon: "🔄" },
  unproductive: { label: "Unproductive", color: "text-orange-400", bgColor: "bg-orange-500/20", icon: "⚠️" },
  detraining: { label: "Detraining", color: "text-red-400", bgColor: "bg-red-500/20", icon: "📉" },
  peaking: { label: "Peaking", color: "text-purple-400", bgColor: "bg-purple-500/20", icon: "🏆" },
  overreaching: { label: "Overreaching", color: "text-amber-400", bgColor: "bg-amber-500/20", icon: "⚡" },
};

// VO2 Max fitness levels
function getVO2MaxLevel(value: number): { level: string; color: string } {
  if (value >= 60) return { level: "Elite", color: "text-purple-400" };
  if (value >= 52) return { level: "Excellent", color: "text-teal-400" };
  if (value >= 45) return { level: "Good", color: "text-green-400" };
  if (value >= 38) return { level: "Fair", color: "text-yellow-400" };
  return { level: "Below Average", color: "text-orange-400" };
}

function getTrendColor(trend: string): string {
  switch (trend) {
    case "improving":
      return "text-green-400";
    case "declining":
      return "text-red-400";
    default:
      return "text-gray-400";
  }
}

export function VO2MaxCard({ vo2maxData, isLoading }: VO2MaxCardProps) {
  const t = useTranslations("vo2max");

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-20 bg-gray-700 rounded-lg" />
        <div className="h-4 bg-gray-700 rounded w-2/3" />
      </div>
    );
  }

  const currentVO2Max = vo2maxData?.current_vo2max_running;
  const trend = vo2maxData?.trend || "unknown";
  const changePercent = vo2maxData?.change_percent || 0;

  // Get latest training status from data points
  const latestDataPoint = vo2maxData?.data_points?.slice(-1)[0];
  const trainingStatus = latestDataPoint?.training_status?.toLowerCase();
  const statusConfig = trainingStatus ? TRAINING_STATUS_CONFIG[trainingStatus] : null;

  if (!currentVO2Max) {
    return (
      <div className="text-center py-6">
        <div className="text-4xl mb-2">💨</div>
        <p className="text-gray-500 text-sm">{t("noData")}</p>
        <p className="text-gray-600 text-xs mt-1">{t("syncGarmin")}</p>
      </div>
    );
  }

  const levelInfo = getVO2MaxLevel(currentVO2Max);
  const trendColor = getTrendColor(trend);

  return (
    <div className="space-y-3">
      {/* Main VO2 Max Value */}
      <div className="relative bg-gradient-to-br from-gray-800 to-gray-900 rounded-xl p-4 border border-gray-700">
        <div className="absolute top-3 right-3">
          <InfoTooltip
            content={
              <div className="w-[280px]">
                <div className="font-semibold text-white mb-1">{t("tooltip.title")}</div>
                <div className="text-gray-300">{t("tooltip.description")}</div>
              </div>
            }
            position="top"
          />
        </div>

        <div className="flex items-center gap-4">
          {/* VO2 Max Circle */}
          <div className="relative w-20 h-20 flex-shrink-0">
            <svg className="w-20 h-20 transform -rotate-90" viewBox="0 0 80 80">
              <circle
                cx="40"
                cy="40"
                r="35"
                fill="none"
                stroke="currentColor"
                strokeWidth="6"
                className="text-gray-700"
              />
              <circle
                cx="40"
                cy="40"
                r="35"
                fill="none"
                stroke="currentColor"
                strokeWidth="6"
                strokeDasharray={`${(currentVO2Max / 80) * 220} 220`}
                strokeLinecap="round"
                className={levelInfo.color}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className={clsx("text-2xl font-bold", levelInfo.color)}>
                {currentVO2Max.toFixed(1)}
              </span>
            </div>
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="text-xs text-gray-500 uppercase tracking-wide">
              {t("title")}
            </div>
            <div className={clsx("text-lg font-semibold mt-1", levelInfo.color)}>
              {levelInfo.level}
            </div>

            {/* Trend indicator */}
            <div className={clsx("flex items-center gap-1 mt-1", trendColor)}>
              {trend === "improving" && (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              )}
              {trend === "declining" && (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
                </svg>
              )}
              {trend === "stable" && (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14" />
                </svg>
              )}
              <span className="text-xs">
                {changePercent > 0 ? "+" : ""}
                {changePercent.toFixed(1)}% {t(`trend.${trend}`)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Training Status Badge */}
      {statusConfig && (
        <div className={clsx(
          "flex items-center justify-center gap-2 py-2 px-3 rounded-lg border",
          statusConfig.bgColor,
          "border-gray-700"
        )}>
          <span className="text-sm">{statusConfig.icon}</span>
          <span className={clsx("text-sm font-medium", statusConfig.color)}>
            {statusConfig.label}
          </span>
          <InfoTooltip
            content={
              <div className="w-[200px] text-xs">
                Training status from Garmin based on your recent workout patterns and fitness trends.
              </div>
            }
            position="top"
          />
        </div>
      )}
    </div>
  );
}
