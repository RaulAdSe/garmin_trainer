"use client";

import { clsx } from "clsx";
import { InfoTooltip } from "@/components/ui/Tooltip";
import { useFitnessMetrics } from "@/hooks/useAthleteContext";
import { useUserProgress } from "@/hooks/useAchievements";
import { StreakCounterCompact } from "@/components/gamification/StreakCounter";

// Metric explanations for fitness metrics
const METRIC_INFO: Record<string, { title: string; description: string }> = {
  ctl: {
    title: "Chronic Training Load (Fitness)",
    description:
      "42-day exponentially weighted average of your training stress. Higher values indicate greater aerobic fitness and capacity to handle training load. Takes weeks to build, days to lose.",
  },
  atl: {
    title: "Acute Training Load (Fatigue)",
    description:
      "7-day exponentially weighted average of your training stress. Represents recent training fatigue. High ATL means you've been training hard recently and may need recovery.",
  },
  tsb: {
    title: "Training Stress Balance (Form)",
    description:
      "The difference between fitness (CTL) and fatigue (ATL). Positive values indicate freshness and readiness to perform. Negative values suggest accumulated fatigue. Target +5 to +25 for peak performance.",
  },
  acwr: {
    title: "Acute:Chronic Workload Ratio",
    description:
      "Ratio of recent load (ATL) to long-term load (CTL). Optimal range is 0.8-1.3. Below 0.8 = undertrained. Above 1.5 = high injury risk. Use this to guide training progression safely.",
  },
  hrss: {
    title: "Heart Rate Stress Score (HRSS)",
    description:
      "A measure of training load based on heart rate intensity and duration. Similar to TSS (Training Stress Score) but calculated from heart rate data. 100 HRSS = 1 hour at lactate threshold. Used to track cumulative training stress.",
  },
};

interface FitnessMetricsProps {
  fitness: {
    ctl: number;
    atl: number;
    tsb: number;
    acwr: number;
    risk_zone: string;
    daily_load: number;
  };
}

export function FitnessMetrics({ fitness }: FitnessMetricsProps) {
  // Fetch 7-day historical data for trend calculation
  const { data: historyData } = useFitnessMetrics(7);
  // Fetch user progress for streak
  const { data: userProgress } = useUserProgress();

  // Calculate trends (compare today vs 7 days ago)
  const ctlTrend = historyData?.metrics && historyData.metrics.length >= 2
    ? fitness.ctl - historyData.metrics[0].ctl
    : null;
  const atlTrend = historyData?.metrics && historyData.metrics.length >= 2
    ? fitness.atl - historyData.metrics[0].atl
    : null;

  // Calculate 4-week comparison for "Rival Ghost"
  const { data: monthData } = useFitnessMetrics(28);
  const pastSelfCTL = monthData?.metrics?.[0]?.ctl;
  const ctlImprovement = pastSelfCTL ? fitness.ctl - pastSelfCTL : null;
  const ctlImprovementPercent = pastSelfCTL && pastSelfCTL > 0
    ? ((fitness.ctl - pastSelfCTL) / pastSelfCTL) * 100
    : null;

  const riskZoneConfig: Record<string, { color: string; label: string }> = {
    optimal: { color: "text-green-400", label: "Optimal" },
    undertrained: { color: "text-blue-400", label: "Undertrained" },
    caution: { color: "text-yellow-400", label: "Caution" },
    danger: { color: "text-red-400", label: "Danger" },
    unknown: { color: "text-gray-400", label: "Unknown" },
  };

  const riskConfig =
    riskZoneConfig[fitness.risk_zone] || riskZoneConfig.unknown;

  return (
    <div className="space-y-4">
      {/* Streak Counter Header */}
      {userProgress?.streak && (
        <div className="flex justify-end -mt-1 -mr-1">
          <StreakCounterCompact
            streakInfo={{
              current: userProgress.streak.current,
              longest: userProgress.streak.longest,
              freeze_tokens: userProgress.streak.freezeTokens,
              protected: userProgress.streak.isProtected,
            }}
          />
        </div>
      )}

      {/* Main metrics */}
      <div className="grid grid-cols-2 gap-4">
        <MetricCard
          label="CTL"
          value={fitness.ctl}
          sublabel="Fitness"
          color="text-teal-400"
          info={METRIC_INFO.ctl}
          trend={ctlTrend}
        />
        <MetricCard
          label="ATL"
          value={fitness.atl}
          sublabel="Fatigue"
          color="text-orange-400"
          info={METRIC_INFO.atl}
          trend={atlTrend}
        />
        <MetricCard
          label="TSB"
          value={fitness.tsb}
          sublabel="Form"
          color={fitness.tsb > 0 ? "text-green-400" : "text-red-400"}
          showSign
          info={METRIC_INFO.tsb}
        />
        <MetricCard
          label="ACWR"
          value={fitness.acwr}
          sublabel="Load Ratio"
          color={riskConfig.color}
          decimals={2}
          info={METRIC_INFO.acwr}
        />
      </div>

      {/* Rival Ghost - You vs Past Self */}
      {pastSelfCTL && ctlImprovement !== null && (
        <div className="border-t border-gray-800 pt-4">
          <RivalGhost
            currentCTL={fitness.ctl}
            pastCTL={pastSelfCTL}
            improvement={ctlImprovement}
            improvementPercent={ctlImprovementPercent}
          />
        </div>
      )}

      {/* Daily Load */}
      <div className="border-t border-gray-800 pt-4">
        <div className="flex justify-between items-center">
          <span className="text-gray-400 flex items-center gap-1">
            Today&apos;s Load
            <InfoTooltip
              content={
                <div className="w-[280px]">
                  <div className="font-semibold text-white mb-1">{METRIC_INFO.hrss.title}</div>
                  <div className="text-gray-300">{METRIC_INFO.hrss.description}</div>
                </div>
              }
              position="top"
            />
          </span>
          <span className="text-white font-mono">
            {fitness.daily_load.toFixed(0)} HRSS
          </span>
        </div>
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  sublabel,
  color,
  showSign = false,
  decimals = 1,
  info,
  trend,
}: {
  label: string;
  value: number;
  sublabel: string;
  color: string;
  showSign?: boolean;
  decimals?: number;
  info?: { title: string; description: string };
  trend?: number | null;
}) {
  const displayValue = showSign && value > 0 ? `+${value.toFixed(decimals)}` : value.toFixed(decimals);

  // Determine trend direction and color
  const getTrendInfo = (trendValue: number | null | undefined) => {
    if (trendValue === null || trendValue === undefined) return null;
    if (Math.abs(trendValue) < 0.5) return { direction: "stable", color: "text-gray-400" };
    if (trendValue > 0) return { direction: "up", color: "text-green-400" };
    return { direction: "down", color: "text-red-400" };
  };

  const trendInfo = getTrendInfo(trend);

  return (
    <div className="bg-gray-800 rounded-lg p-3 relative">
      {info && (
        <div className="absolute top-2 right-2">
          <InfoTooltip
            content={
              <div className="w-[280px]">
                <div className="font-semibold text-white mb-1">{info.title}</div>
                <div className="text-gray-300">{info.description}</div>
              </div>
            }
            position="top"
          />
        </div>
      )}
      <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
      <div className="flex items-center gap-2">
        <div className={clsx("text-2xl font-bold font-mono", color)}>
          {displayValue}
        </div>
        {/* Trend Arrow */}
        {trendInfo && (
          <div className={clsx("flex items-center", trendInfo.color)}>
            {trendInfo.direction === "up" && (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
              </svg>
            )}
            {trendInfo.direction === "down" && (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
              </svg>
            )}
            {trendInfo.direction === "stable" && (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14" />
              </svg>
            )}
            {trend !== null && trend !== undefined && (
              <span className="text-xs ml-0.5 font-medium">
                {trend > 0 ? "+" : ""}{trend.toFixed(1)}
              </span>
            )}
          </div>
        )}
      </div>
      <div className="text-xs text-gray-500">{sublabel}</div>
    </div>
  );
}

// RivalGhost - Compare yourself vs 4 weeks ago
function RivalGhost({
  currentCTL,
  pastCTL,
  improvement,
  improvementPercent,
}: {
  currentCTL: number;
  pastCTL: number;
  improvement: number;
  improvementPercent: number | null;
}) {
  const isWinning = improvement >= 0;
  const maxCTL = Math.max(currentCTL, pastCTL, 1);

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400 uppercase tracking-wide flex items-center gap-1.5">
          <span className="opacity-50">👻</span>
          You vs Past Self
          <span className="text-gray-600">(4 weeks ago)</span>
        </span>
        {isWinning ? (
          <span className="text-xs font-medium text-green-400 flex items-center gap-1">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            Winning
          </span>
        ) : (
          <span className="text-xs font-medium text-orange-400 flex items-center gap-1">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Catch up!
          </span>
        )}
      </div>

      {/* Progress Bars */}
      <div className="space-y-2">
        {/* Current (You) */}
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-300 w-12">You</span>
          <div className="flex-1 h-3 bg-gray-800 rounded-full overflow-hidden relative">
            <div
              className={clsx(
                "h-full rounded-full transition-all duration-700 ease-out",
                isWinning
                  ? "bg-gradient-to-r from-teal-500 to-green-400"
                  : "bg-gradient-to-r from-orange-500 to-yellow-400"
              )}
              style={{ width: `${(currentCTL / maxCTL) * 100}%` }}
            >
              {/* Shimmer effect */}
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-pulse" />
            </div>
          </div>
          <span className="text-sm font-mono text-white w-10 text-right">{currentCTL.toFixed(0)}</span>
        </div>

        {/* Past Self (Ghost) */}
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500 w-12">Ghost</span>
          <div className="flex-1 h-3 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gray-600/50 rounded-full"
              style={{ width: `${(pastCTL / maxCTL) * 100}%` }}
            />
          </div>
          <span className="text-sm font-mono text-gray-500 w-10 text-right">{pastCTL.toFixed(0)}</span>
        </div>
      </div>

      {/* Delta Summary */}
      <div className="flex items-center justify-center gap-2 pt-1">
        <span
          className={clsx(
            "text-lg font-bold",
            isWinning ? "text-green-400" : "text-orange-400"
          )}
        >
          {improvement > 0 ? "+" : ""}{improvement.toFixed(1)}
        </span>
        <span className="text-gray-400 text-sm">CTL</span>
        {improvementPercent !== null && (
          <span
            className={clsx(
              "text-xs px-1.5 py-0.5 rounded",
              isWinning ? "bg-green-900/30 text-green-400" : "bg-orange-900/30 text-orange-400"
            )}
          >
            {improvementPercent > 0 ? "+" : ""}{improvementPercent.toFixed(0)}%
          </span>
        )}
      </div>

      {/* Motivational message */}
      <p className="text-center text-xs text-gray-500">
        {isWinning
          ? improvement > 5
            ? "You're crushing it! Keep up the momentum."
            : "Slight edge over your past self. Stay consistent!"
          : "Time to step it up! Your past self is ahead."}
      </p>
    </div>
  );
}
