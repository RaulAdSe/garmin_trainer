"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { clsx } from "clsx";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { InfoTooltip } from "@/components/ui/Tooltip";
import type { RacePrediction } from "./VDOTCalculator";

// Race distance icons/colors
const RACE_STYLES: Record<string, {
  icon: string;
  color: string;
  bg: string;
  highlight?: boolean;
}> = {
  "5K": {
    icon: "5K",
    color: "text-green-400",
    bg: "bg-green-900/20",
  },
  "10K": {
    icon: "10K",
    color: "text-blue-400",
    bg: "bg-blue-900/20",
  },
  "Half Marathon": {
    icon: "HM",
    color: "text-purple-400",
    bg: "bg-purple-900/20",
  },
  "Marathon": {
    icon: "FM",
    color: "text-amber-400",
    bg: "bg-amber-900/20",
    highlight: true,
  },
};

type PaceUnit = "km" | "mile";

interface RacePredictionsProps {
  predictions: RacePrediction[];
  vdot?: number;
  sourceRace?: {
    distance: string;
    time: string;
  };
  showHeader?: boolean;
  compact?: boolean;
}

export function RacePredictions({
  predictions,
  vdot,
  sourceRace,
  showHeader = true,
  compact = false,
}: RacePredictionsProps) {
  const t = useTranslations("paceZones");
  const [paceUnit, setPaceUnit] = useState<PaceUnit>("km");

  // Format pace based on unit
  const formatPace = (pred: RacePrediction): string => {
    if (paceUnit === "mile") {
      return pred.pace_per_mile;
    }
    return pred.pace_formatted;
  };

  // Check if this prediction matches the source race
  const isSourceRace = (pred: RacePrediction): boolean => {
    if (!sourceRace) return false;
    return pred.distance.toLowerCase().includes(sourceRace.distance.toLowerCase());
  };

  return (
    <Card className={clsx(compact && "p-4")}>
      {showHeader && (
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CardTitle>{t("predictions.title")}</CardTitle>
              <InfoTooltip
                content={
                  <div className="w-[280px]">
                    <div className="font-semibold text-white mb-1">
                      {t("predictions.howItWorks")}
                    </div>
                    <div className="text-gray-300">
                      {t("predictions.howItWorksDesc")}
                    </div>
                  </div>
                }
                position="right"
              />
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
                /km
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
                /mi
              </button>
            </div>
          </div>
          <CardDescription>
            {vdot
              ? t("predictions.basedOnVdot", { vdot })
              : t("predictions.subtitle")}
          </CardDescription>
        </CardHeader>
      )}

      <div className="grid grid-cols-2 gap-3">
        {predictions.map((pred) => {
          const style = RACE_STYLES[pred.distance] || {
            icon: pred.distance.substring(0, 2),
            color: "text-gray-400",
            bg: "bg-gray-800",
          };
          const isSource = isSourceRace(pred);

          return (
            <div
              key={pred.distance}
              className={clsx(
                "relative p-4 rounded-lg border transition-all",
                style.bg,
                isSource
                  ? "border-teal-500 ring-1 ring-teal-500/30"
                  : "border-gray-700/30 hover:border-gray-600/50"
              )}
            >
              {/* Source Race Badge */}
              {isSource && (
                <div className="absolute -top-2 -right-2 px-2 py-0.5 bg-teal-600 text-white text-xs rounded-full">
                  {t("predictions.source")}
                </div>
              )}

              {/* Distance Badge */}
              <div className="flex items-center gap-2 mb-2">
                <span
                  className={clsx(
                    "px-2 py-0.5 text-xs font-bold rounded",
                    style.bg,
                    style.color
                  )}
                >
                  {style.icon}
                </span>
                <span className="text-sm text-gray-300">{pred.distance}</span>
              </div>

              {/* Predicted Time */}
              <div className="text-2xl font-bold font-mono text-white mb-1">
                {pred.time_formatted}
              </div>

              {/* Pace */}
              <div className="text-sm text-gray-400">
                {formatPace(pred)}
              </div>
            </div>
          );
        })}
      </div>

      {/* Disclaimer */}
      <div className="mt-4 p-3 bg-gray-800/50 rounded-lg">
        <div className="text-xs text-gray-500 flex items-start gap-2">
          <svg
            className="w-4 h-4 text-gray-600 mt-0.5 shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span>{t("predictions.disclaimer")}</span>
        </div>
      </div>
    </Card>
  );
}

// Compact list version for sidebars
export function RacePredictionsCompact({
  predictions,
}: {
  predictions: RacePrediction[];
}) {
  const t = useTranslations("paceZones");

  return (
    <div className="space-y-2">
      <div className="text-sm font-medium text-gray-300 mb-2">
        {t("predictions.title")}
      </div>

      {predictions.map((pred) => {
        const style = RACE_STYLES[pred.distance] || {
          color: "text-gray-400",
        };

        return (
          <div
            key={pred.distance}
            className="flex items-center justify-between py-1.5 px-2 rounded bg-gray-800/50"
          >
            <span className={clsx("text-sm", style.color)}>{pred.distance}</span>
            <span className="text-sm font-mono text-white">
              {pred.time_formatted}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// Table version for detailed view
export function RacePredictionsTable({
  predictions,
  paceUnit = "km",
}: {
  predictions: RacePrediction[];
  paceUnit?: PaceUnit;
}) {
  const t = useTranslations("paceZones");

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700">
            <th className="text-left py-2 px-3 text-gray-400 font-medium">
              {t("predictions.distance")}
            </th>
            <th className="text-right py-2 px-3 text-gray-400 font-medium">
              {t("predictions.time")}
            </th>
            <th className="text-right py-2 px-3 text-gray-400 font-medium">
              {t("predictions.pace")}
            </th>
          </tr>
        </thead>
        <tbody>
          {predictions.map((pred) => {
            const style = RACE_STYLES[pred.distance] || {
              color: "text-gray-300",
            };

            return (
              <tr
                key={pred.distance}
                className="border-b border-gray-800 hover:bg-gray-800/50"
              >
                <td className={clsx("py-2 px-3 font-medium", style.color)}>
                  {pred.distance}
                  <span className="text-gray-600 text-xs ml-1">
                    ({pred.distance_km.toFixed(1)}km)
                  </span>
                </td>
                <td className="py-2 px-3 text-right font-mono text-white">
                  {pred.time_formatted}
                </td>
                <td className="py-2 px-3 text-right font-mono text-gray-300">
                  {paceUnit === "mile" ? pred.pace_per_mile : pred.pace_formatted}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default RacePredictions;
