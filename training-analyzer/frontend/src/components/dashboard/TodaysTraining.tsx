"use client";

import { cn } from "@/lib/utils";
import { InfoTooltip } from "@/components/ui/Tooltip";

interface TodaysTrainingProps {
  fitness: {
    ctl: number;
    atl: number;
    tsb: number;
    acwr: number;
    risk_zone: string;
    daily_load: number;
  };
}

// ACWR risk zone configuration
const ACWR_CONFIG = {
  optimal: { color: "text-green-400", bgColor: "bg-green-500/20", label: "Safe Zone", icon: "check" },
  undertrained: { color: "text-blue-400", bgColor: "bg-blue-500/20", label: "Undertrained", icon: "minus" },
  caution: { color: "text-yellow-400", bgColor: "bg-yellow-500/20", label: "Caution", icon: "alert" },
  danger: { color: "text-red-400", bgColor: "bg-red-500/20", label: "High Risk", icon: "warning" },
} as const;

// TSB interpretation
function getTSBInterpretation(tsb: number): { label: string; color: string; description: string } {
  if (tsb >= 15) return { label: "Very Fresh", color: "text-green-400", description: "Peak performance window" };
  if (tsb >= 5) return { label: "Fresh", color: "text-green-400", description: "Ready for quality work" };
  if (tsb >= -10) return { label: "Neutral", color: "text-gray-400", description: "Balanced state" };
  if (tsb >= -25) return { label: "Fatigued", color: "text-orange-400", description: "Accumulated fatigue" };
  return { label: "Very Fatigued", color: "text-red-400", description: "Consider recovery" };
}

export function TodaysTraining({ fitness }: TodaysTrainingProps) {
  const { tsb, acwr, risk_zone, ctl, daily_load } = fitness;

  // Calculate recommended load range (80% to 130% of CTL for safe progression)
  const minLoad = Math.round(ctl * 0.8);
  const maxLoad = Math.round(ctl * 1.3);

  const riskConfig = ACWR_CONFIG[risk_zone as keyof typeof ACWR_CONFIG] || ACWR_CONFIG.optimal;
  const tsbInfo = getTSBInterpretation(tsb);

  return (
    <div className="space-y-4">
      {/* ACWR - Load Ratio */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">Load Ratio (ACWR)</span>
          <InfoTooltip
            content={
              <div className="w-[220px]">
                <div className="font-semibold text-white mb-1">Acute:Chronic Workload Ratio</div>
                <div className="text-gray-300 text-xs">
                  Optimal: 0.8-1.3. Below 0.8 = undertrained. Above 1.5 = injury risk.
                </div>
              </div>
            }
            position="top"
          />
        </div>
        <div className="flex items-center gap-2">
          <span className={cn("text-lg font-bold font-mono", riskConfig.color)}>
            {acwr.toFixed(2)}
          </span>
          <span
            className={cn(
              "px-2 py-0.5 text-xs font-medium rounded",
              riskConfig.bgColor,
              riskConfig.color
            )}
          >
            {riskConfig.icon === "check" && (
              <svg className="w-3 h-3 inline mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            )}
            {riskConfig.icon === "alert" && (
              <svg className="w-3 h-3 inline mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            )}
            {riskConfig.label}
          </span>
        </div>
      </div>

      {/* TSB - Form */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">Form (TSB)</span>
          <InfoTooltip
            content={
              <div className="w-[220px]">
                <div className="font-semibold text-white mb-1">Training Stress Balance</div>
                <div className="text-gray-300 text-xs">
                  {tsbInfo.description}. Target +5 to +25 for peak performance.
                </div>
              </div>
            }
            position="top"
          />
        </div>
        <div className="flex items-center gap-2">
          <span className={cn("text-lg font-bold font-mono", tsbInfo.color)}>
            {tsb > 0 ? "+" : ""}{tsb.toFixed(0)}
          </span>
          <span className={cn("text-sm", tsbInfo.color)}>
            {tsbInfo.label}
          </span>
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-gray-800" />

      {/* Recommended Load */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-400">Recommended Load</span>
          <span className="text-sm font-mono text-teal-400">
            {minLoad}-{maxLoad} HRSS
          </span>
        </div>

        {/* Load progress indicator */}
        <div className="relative h-2 bg-gray-800 rounded-full overflow-hidden">
          {/* Safe zone indicator */}
          <div
            className="absolute h-full bg-teal-900/50"
            style={{
              left: `${(minLoad / (ctl * 2)) * 100}%`,
              width: `${((maxLoad - minLoad) / (ctl * 2)) * 100}%`,
            }}
          />
          {/* Current load marker */}
          {daily_load > 0 && (
            <div
              className={cn(
                "absolute top-1/2 -translate-y-1/2 w-2 h-4 rounded-sm",
                daily_load >= minLoad && daily_load <= maxLoad
                  ? "bg-teal-400"
                  : daily_load > maxLoad
                  ? "bg-red-400"
                  : "bg-blue-400"
              )}
              style={{
                left: `${Math.min((daily_load / (ctl * 2)) * 100, 98)}%`,
              }}
            />
          )}
        </div>

        {/* Today's actual load */}
        {daily_load > 0 && (
          <div className="flex justify-between mt-1 text-xs">
            <span className="text-gray-500">Today: {daily_load.toFixed(0)} HRSS</span>
            <span className={cn(
              daily_load >= minLoad && daily_load <= maxLoad
                ? "text-teal-400"
                : daily_load > maxLoad
                ? "text-red-400"
                : "text-blue-400"
            )}>
              {daily_load >= minLoad && daily_load <= maxLoad
                ? "On target"
                : daily_load > maxLoad
                ? "Above target"
                : "Below target"}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

// Skeleton loader
export function TodaysTrainingSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="flex justify-between">
        <div className="w-24 h-4 bg-gray-800 rounded" />
        <div className="w-20 h-6 bg-gray-800 rounded" />
      </div>
      <div className="flex justify-between">
        <div className="w-20 h-4 bg-gray-800 rounded" />
        <div className="w-16 h-6 bg-gray-800 rounded" />
      </div>
      <div className="border-t border-gray-800" />
      <div>
        <div className="flex justify-between mb-2">
          <div className="w-28 h-4 bg-gray-800 rounded" />
          <div className="w-24 h-4 bg-gray-800 rounded" />
        </div>
        <div className="h-2 bg-gray-800 rounded-full" />
      </div>
    </div>
  );
}
