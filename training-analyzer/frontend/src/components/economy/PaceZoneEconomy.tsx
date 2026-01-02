"use client";

import { clsx } from "clsx";
import { useTranslations } from "next-intl";
import { InfoTooltip } from "@/components/ui/Tooltip";
import { usePaceZonesEconomy } from "@/hooks/useRunningEconomy";

interface PaceZone {
  paceZone: string;
  zoneName: string;
  avgEconomy: number;
  bestEconomy: number;
  worstEconomy: number;
  workoutCount: number;
  improvement: number;
  paceRange?: string;
  hrRange?: string;
}

interface PaceZoneEconomyProps {
  days?: number;
  className?: string;
}

// Zone colors for consistent styling
const ZONE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  easy: { bg: "bg-green-900/30", text: "text-green-400", border: "border-green-500/30" },
  long: { bg: "bg-teal-900/30", text: "text-teal-400", border: "border-teal-500/30" },
  tempo: { bg: "bg-yellow-900/30", text: "text-yellow-400", border: "border-yellow-500/30" },
  threshold: { bg: "bg-orange-900/30", text: "text-orange-400", border: "border-orange-500/30" },
  interval: { bg: "bg-red-900/30", text: "text-red-400", border: "border-red-500/30" },
};

export function PaceZoneEconomy({ days = 90, className }: PaceZoneEconomyProps) {
  const t = useTranslations("economy");
  const { data, isLoading, error } = usePaceZonesEconomy(days);

  if (isLoading) {
    return (
      <div className={clsx("bg-gray-900 rounded-xl p-4 animate-pulse", className)}>
        <div className="h-4 bg-gray-800 rounded w-1/3 mb-4" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-gray-800 rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !data?.zonesEconomy) {
    return (
      <div className={clsx("bg-gray-900 rounded-xl p-4", className)}>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-gray-400 text-sm">{t("zonesTitle")}</span>
          <InfoTooltip
            content={
              <div className="w-[280px]">
                <div className="font-semibold text-white mb-1">{t("zonesTooltipTitle")}</div>
                <div className="text-gray-300">{t("zonesTooltipDescription")}</div>
              </div>
            }
            position="top"
          />
        </div>
        <p className="text-gray-500 text-sm">{t("noZonesData")}</p>
      </div>
    );
  }

  const zonesEconomy = data.zonesEconomy;
  const zones: PaceZone[] = zonesEconomy.zones;

  if (zones.length === 0) {
    return (
      <div className={clsx("bg-gray-900 rounded-xl p-4", className)}>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-gray-400 text-sm">{t("zonesTitle")}</span>
        </div>
        <p className="text-gray-500 text-sm">{t("noZonesData")}</p>
      </div>
    );
  }

  // Find best economy for comparison bar
  const bestEconomy = Math.min(...zones.map((z: PaceZone) => z.bestEconomy));
  const worstEconomy = Math.max(...zones.map((z: PaceZone) => z.worstEconomy));
  const range = worstEconomy - bestEconomy || 0.1;

  return (
    <div className={clsx("bg-gray-900 rounded-xl p-4", className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-gray-300 text-sm font-medium">{t("zonesTitle")}</span>
          <InfoTooltip
            content={
              <div className="w-[280px]">
                <div className="font-semibold text-white mb-1">{t("zonesTooltipTitle")}</div>
                <div className="text-gray-300">{t("zonesTooltipDescription")}</div>
              </div>
            }
            position="top"
          />
        </div>
        <span className="text-xs text-gray-500">
          {t("totalWorkouts", { count: zonesEconomy.totalWorkouts })}
        </span>
      </div>

      {/* Best zone highlight */}
      {zonesEconomy.bestZone && (
        <div className="mb-4 px-3 py-2 bg-green-900/20 border border-green-500/30 rounded-lg">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-green-400" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
            <span className="text-sm text-green-400">
              {t("bestZone")}: <span className="font-medium capitalize">{zonesEconomy.bestZone}</span>
            </span>
          </div>
        </div>
      )}

      {/* Zone list */}
      <div className="space-y-3">
        {zones.map((zone) => {
          const zoneStyle = ZONE_COLORS[zone.paceZone] || ZONE_COLORS.easy;
          const isBest = zone.paceZone === zonesEconomy.bestZone;

          // Calculate bar width relative to economy range (inverted - lower is better)
          const economyPosition = ((zone.avgEconomy - bestEconomy) / range) * 100;
          const barWidth = Math.max(10, 100 - economyPosition);

          return (
            <div
              key={zone.paceZone}
              className={clsx(
                "rounded-lg p-3 border transition-all",
                zoneStyle.bg,
                zoneStyle.border,
                isBest && "ring-1 ring-green-500/50"
              )}
            >
              {/* Zone header */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className={clsx("font-medium", zoneStyle.text)}>{zone.zoneName}</span>
                  <span className="text-xs text-gray-500">({zone.workoutCount} runs)</span>
                </div>
                <span className={clsx("font-mono text-lg font-bold", zoneStyle.text)}>
                  {zone.avgEconomy.toFixed(2)}
                </span>
              </div>

              {/* Economy bar */}
              <div className="h-2 bg-gray-800 rounded-full overflow-hidden mb-2">
                <div
                  className={clsx("h-full rounded-full transition-all duration-500", zoneStyle.text.replace("text-", "bg-"))}
                  style={{ width: `${barWidth}%` }}
                />
              </div>

              {/* Details */}
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div>
                  <span className="text-gray-500">{t("paceRange")}</span>
                  <div className="text-gray-300 font-mono">{zone.paceRange || "-"}</div>
                </div>
                <div>
                  <span className="text-gray-500">{t("hrRange")}</span>
                  <div className="text-gray-300 font-mono">{zone.hrRange || "-"}</div>
                </div>
                <div className="text-right">
                  <span className="text-gray-500">{t("bestEconomy")}</span>
                  <div className="text-green-400 font-mono">{zone.bestEconomy.toFixed(2)}</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="mt-4 pt-3 border-t border-gray-800">
        <p className="text-xs text-gray-500 text-center">
          {t("economyExplanation")}
        </p>
      </div>
    </div>
  );
}

export default PaceZoneEconomy;
