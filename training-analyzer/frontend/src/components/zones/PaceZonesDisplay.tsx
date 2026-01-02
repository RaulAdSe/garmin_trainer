"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { clsx } from "clsx";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { InfoTooltip } from "@/components/ui/Tooltip";
import type { PaceZone } from "./VDOTCalculator";

// Zone colors following the existing pattern
const ZONE_COLORS: Record<string, {
  bg: string;
  border: string;
  text: string;
  bar: string;
}> = {
  easy: {
    bg: "bg-green-900/20",
    border: "border-green-700/30",
    text: "text-green-400",
    bar: "bg-green-500",
  },
  marathon: {
    bg: "bg-blue-900/20",
    border: "border-blue-700/30",
    text: "text-blue-400",
    bar: "bg-blue-500",
  },
  threshold: {
    bg: "bg-yellow-900/20",
    border: "border-yellow-700/30",
    text: "text-yellow-400",
    bar: "bg-yellow-500",
  },
  interval: {
    bg: "bg-orange-900/20",
    border: "border-orange-700/30",
    text: "text-orange-400",
    bar: "bg-orange-500",
  },
  repetition: {
    bg: "bg-red-900/20",
    border: "border-red-700/30",
    text: "text-red-400",
    bar: "bg-red-500",
  },
};

// Zone display order
const ZONE_ORDER = ["easy", "marathon", "threshold", "interval", "repetition"];

type PaceUnit = "km" | "mile";

interface PaceZonesDisplayProps {
  zones: Record<string, PaceZone>;
  vdot?: number;
  showHeader?: boolean;
  compact?: boolean;
}

export function PaceZonesDisplay({
  zones,
  vdot,
  showHeader = true,
  compact = false,
}: PaceZonesDisplayProps) {
  const t = useTranslations("paceZones");
  const [paceUnit, setPaceUnit] = useState<PaceUnit>("km");

  // Sort zones by the defined order
  const orderedZones = ZONE_ORDER.map((key) => ({
    key,
    zone: zones[key],
  })).filter((item) => item.zone);

  // Calculate max pace for visualization scale
  const maxPace = Math.max(...orderedZones.map((z) => z.zone.min_pace_sec_per_km));
  const minPace = Math.min(...orderedZones.map((z) => z.zone.max_pace_sec_per_km));

  // Format pace based on unit
  const formatPace = (zone: PaceZone): string => {
    if (paceUnit === "mile") {
      return `${zone.max_pace_per_mile} - ${zone.min_pace_per_mile}`;
    }
    return `${zone.max_pace_formatted} - ${zone.min_pace_formatted}/km`;
  };

  // Calculate bar width percentage (inverted - faster pace = longer bar)
  const getBarWidth = (zone: PaceZone): number => {
    const range = maxPace - minPace;
    if (range === 0) return 50;
    // Invert: faster pace (lower seconds) = higher percentage
    const avgPace = (zone.min_pace_sec_per_km + zone.max_pace_sec_per_km) / 2;
    const invertedPosition = maxPace - avgPace;
    return Math.min(100, Math.max(20, (invertedPosition / range) * 100 + 30));
  };

  return (
    <Card className={clsx(compact && "p-4")}>
      {showHeader && (
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CardTitle>{t("zones.title")}</CardTitle>
              {vdot && (
                <span className="px-2 py-0.5 text-sm font-mono bg-teal-900/30 text-teal-400 rounded">
                  VDOT {vdot}
                </span>
              )}
            </div>
            {/* Pace Unit Toggle */}
            <div className="flex items-center gap-1 bg-gray-800 rounded-lg p-1">
              <button
                onClick={() => setPaceUnit("km")}
                className={clsx(
                  "px-3 py-1 text-sm rounded transition-colors",
                  paceUnit === "km"
                    ? "bg-gray-700 text-white"
                    : "text-gray-400 hover:text-white"
                )}
              >
                min/km
              </button>
              <button
                onClick={() => setPaceUnit("mile")}
                className={clsx(
                  "px-3 py-1 text-sm rounded transition-colors",
                  paceUnit === "mile"
                    ? "bg-gray-700 text-white"
                    : "text-gray-400 hover:text-white"
                )}
              >
                min/mi
              </button>
            </div>
          </div>
          <CardDescription>{t("zones.subtitle")}</CardDescription>
        </CardHeader>
      )}

      <div className="space-y-3">
        {orderedZones.map(({ key, zone }) => {
          const colors = ZONE_COLORS[key] || ZONE_COLORS.easy;

          return (
            <div
              key={key}
              className={clsx(
                "p-3 rounded-lg border transition-all hover:scale-[1.01]",
                colors.bg,
                colors.border
              )}
            >
              {/* Zone Header */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className={clsx("font-semibold", colors.text)}>
                    {zone.name}
                  </span>
                  <InfoTooltip
                    content={
                      <div className="w-[260px]">
                        <div className="font-semibold text-white mb-1">
                          {zone.name} {t("zones.zone")}
                        </div>
                        <div className="text-gray-300 mb-2">{zone.description}</div>
                        <div className="text-xs text-gray-400">
                          {t("zones.typicalDuration")}: {zone.typical_duration}
                        </div>
                      </div>
                    }
                    position="right"
                  />
                </div>
                <div className="text-sm text-gray-400">
                  {zone.hr_range_min}-{zone.hr_range_max}% {t("zones.maxHr")}
                </div>
              </div>

              {/* Pace Range Bar */}
              <div className="relative h-6 bg-gray-800/50 rounded overflow-hidden mb-2">
                <div
                  className={clsx(
                    "absolute left-0 top-0 h-full rounded transition-all duration-500",
                    colors.bar
                  )}
                  style={{ width: `${getBarWidth(zone)}%` }}
                />
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="font-mono text-sm text-white font-medium drop-shadow-md">
                    {formatPace(zone)}
                  </span>
                </div>
              </div>

              {/* Zone Description */}
              <div className="text-xs text-gray-400 truncate">{zone.description}</div>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="mt-4 pt-4 border-t border-gray-800">
        <div className="flex flex-wrap gap-4 justify-center text-xs text-gray-500">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded bg-green-500" />
            <span>{t("zones.aerobic")}</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded bg-yellow-500" />
            <span>{t("zones.threshold")}</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded bg-orange-500" />
            <span>{t("zones.vo2max")}</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded bg-red-500" />
            <span>{t("zones.anaerobic")}</span>
          </div>
        </div>
      </div>
    </Card>
  );
}

// Compact version for sidebars
export function PaceZonesCompact({
  zones,
  vdot,
}: {
  zones: Record<string, PaceZone>;
  vdot?: number;
}) {
  const t = useTranslations("paceZones");

  const orderedZones = ZONE_ORDER.map((key) => ({
    key,
    zone: zones[key],
  })).filter((item) => item.zone);

  return (
    <div className="space-y-2">
      {vdot && (
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm text-gray-400">{t("zones.yourVdot")}</span>
          <span className="font-mono font-bold text-teal-400">{vdot}</span>
        </div>
      )}

      {orderedZones.slice(0, 3).map(({ key, zone }) => {
        const colors = ZONE_COLORS[key] || ZONE_COLORS.easy;

        return (
          <div
            key={key}
            className="flex items-center justify-between py-1.5 px-2 rounded bg-gray-800/50"
          >
            <span className={clsx("text-sm", colors.text)}>{zone.name}</span>
            <span className="text-sm font-mono text-white">
              {zone.max_pace_formatted} - {zone.min_pace_formatted}
            </span>
          </div>
        );
      })}

      {orderedZones.length > 3 && (
        <div className="text-xs text-gray-500 text-center">
          +{orderedZones.length - 3} {t("zones.moreZones")}
        </div>
      )}
    </div>
  );
}

export default PaceZonesDisplay;
