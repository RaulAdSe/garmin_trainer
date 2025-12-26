"use client";

import { clsx } from "clsx";

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
      {/* Main metrics */}
      <div className="grid grid-cols-2 gap-4">
        <MetricCard
          label="CTL"
          value={fitness.ctl}
          sublabel="Fitness"
          color="text-teal-400"
        />
        <MetricCard
          label="ATL"
          value={fitness.atl}
          sublabel="Fatigue"
          color="text-orange-400"
        />
        <MetricCard
          label="TSB"
          value={fitness.tsb}
          sublabel="Form"
          color={fitness.tsb > 0 ? "text-green-400" : "text-red-400"}
          showSign
        />
        <MetricCard
          label="ACWR"
          value={fitness.acwr}
          sublabel="Load Ratio"
          color={riskConfig.color}
          decimals={2}
        />
      </div>

      {/* Risk Zone */}
      <div className="border-t border-gray-800 pt-4">
        <div className="flex justify-between items-center">
          <span className="text-gray-400">Risk Zone</span>
          <span className={clsx("font-semibold", riskConfig.color)}>
            {riskConfig.label}
          </span>
        </div>
        <ACWRBar acwr={fitness.acwr} />
      </div>

      {/* Daily Load */}
      <div className="border-t border-gray-800 pt-4">
        <div className="flex justify-between items-center">
          <span className="text-gray-400">Today&apos;s Load</span>
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
}: {
  label: string;
  value: number;
  sublabel: string;
  color: string;
  showSign?: boolean;
  decimals?: number;
}) {
  const displayValue = showSign && value > 0 ? `+${value.toFixed(decimals)}` : value.toFixed(decimals);

  return (
    <div className="bg-gray-800 rounded-lg p-3">
      <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
      <div className={clsx("text-2xl font-bold font-mono", color)}>
        {displayValue}
      </div>
      <div className="text-xs text-gray-500">{sublabel}</div>
    </div>
  );
}

function ACWRBar({ acwr }: { acwr: number }) {
  // ACWR zones: <0.8 undertrained, 0.8-1.3 optimal, 1.3-1.5 caution, >1.5 danger
  // Map ACWR to position (0-100%)
  const position = Math.min(100, Math.max(0, ((acwr - 0.5) / 1.5) * 100));

  return (
    <div className="mt-2">
      <div className="relative h-2 bg-gray-800 rounded-full overflow-hidden">
        {/* Zone colors */}
        <div className="absolute inset-0 flex">
          <div className="w-[20%] bg-blue-600" /> {/* <0.8 undertrained */}
          <div className="w-[34%] bg-green-600" /> {/* 0.8-1.3 optimal */}
          <div className="w-[13%] bg-yellow-600" /> {/* 1.3-1.5 caution */}
          <div className="w-[33%] bg-red-600" /> {/* >1.5 danger */}
        </div>
        {/* Position indicator */}
        <div
          className="absolute top-0 w-1 h-full bg-white shadow-lg"
          style={{ left: `${position}%`, transform: "translateX(-50%)" }}
        />
      </div>
      <div className="flex justify-between text-xs text-gray-500 mt-1">
        <span>0.5</span>
        <span>0.8</span>
        <span>1.3</span>
        <span>1.5</span>
        <span>2.0</span>
      </div>
    </div>
  );
}
