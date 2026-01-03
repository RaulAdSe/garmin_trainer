"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { clsx } from "clsx";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { InfoTooltip } from "@/components/ui/Tooltip";
import { VDOTCalculator, type VDOTResult, type PaceZone } from "./VDOTCalculator";
import { PaceZonesCompact } from "./PaceZonesDisplay";

// Zone colors for display
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

const ZONE_ORDER = ["easy", "marathon", "threshold", "interval", "repetition"];

interface SavedZonesData {
  vdot: number;
  source_distance: string;
  source_time_formatted: string;
  pace_zones: Record<string, PaceZone>;
  updated_at: string;
}

interface PaceZonesCardProps {
  className?: string;
  showCalculator?: boolean;
  compact?: boolean;
  onZonesCalculated?: (result: VDOTResult) => void;
  onZonesSaved?: (result: VDOTResult) => void;
}

export function PaceZonesCard({
  className,
  showCalculator: initialShowCalculator = false,
  compact = false,
  onZonesCalculated,
  onZonesSaved,
}: PaceZonesCardProps) {
  const t = useTranslations("paceZones");

  const [savedZones, setSavedZones] = useState<SavedZonesData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCalculator, setShowCalculator] = useState(initialShowCalculator);
  const [calculatedResult, setCalculatedResult] = useState<VDOTResult | null>(null);

  // Fetch saved zones on mount
  const fetchSavedZones = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/v1/pace-zones/my-zones", {
        method: "GET",
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        if (data && data.vdot) {
          setSavedZones(data);
        } else {
          setSavedZones(null);
        }
      } else if (response.status !== 404) {
        throw new Error("Failed to fetch pace zones");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load pace zones");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSavedZones();
  }, [fetchSavedZones]);

  // Handle calculation result
  const handleCalculate = useCallback((result: VDOTResult) => {
    setCalculatedResult(result);
    onZonesCalculated?.(result);
  }, [onZonesCalculated]);

  // Handle save
  const handleSave = useCallback((result: VDOTResult) => {
    setSavedZones({
      vdot: result.vdot,
      source_distance: result.race_distance,
      source_time_formatted: result.race_time_formatted,
      pace_zones: result.pace_zones,
      updated_at: new Date().toISOString(),
    });
    setShowCalculator(false);
    setCalculatedResult(null);
    onZonesSaved?.(result);
  }, [onZonesSaved]);

  // Format date for display
  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return dateString;
    }
  };

  // Get zones to display (saved or just calculated)
  const displayZones = calculatedResult?.pace_zones || savedZones?.pace_zones;
  const displayVdot = calculatedResult?.vdot || savedZones?.vdot;

  if (isLoading) {
    return (
      <Card className={clsx("flex items-center justify-center min-h-[200px]", className)}>
        <LoadingSpinner size="md" />
      </Card>
    );
  }

  // Show calculator view
  if (showCalculator) {
    return (
      <div className={className}>
        <VDOTCalculator
          onCalculate={handleCalculate}
          onSave={handleSave}
          savedVdot={savedZones?.vdot}
          compact={compact}
        />
        {savedZones && (
          <div className="mt-4">
            <Button
              variant="ghost"
              className="w-full text-gray-400"
              onClick={() => {
                setShowCalculator(false);
                setCalculatedResult(null);
              }}
            >
              {t("common.cancel", { fallback: "Cancel" })}
            </Button>
          </div>
        )}
      </div>
    );
  }

  // Empty state - no saved zones
  if (!savedZones) {
    return (
      <Card className={clsx("text-center py-8", className)}>
        <CardHeader>
          <CardTitle>{t("card.title")}</CardTitle>
          <CardDescription>{t("card.subtitle")}</CardDescription>
        </CardHeader>

        <div className="px-6 pb-6">
          <div className="mb-6">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-teal-900/30 flex items-center justify-center">
              <svg
                className="w-8 h-8 text-teal-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
            </div>
            <p className="text-gray-400 text-sm mb-2">{t("card.noZones")}</p>
            <p className="text-gray-500 text-xs">{t("card.noZonesDesc")}</p>
          </div>

          <Button
            onClick={() => setShowCalculator(true)}
            className="bg-gradient-to-r from-teal-500 to-green-500 hover:from-teal-400 hover:to-green-400"
          >
            {t("card.calculateButton")}
          </Button>
        </div>
      </Card>
    );
  }

  // Display saved zones
  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle>{t("card.title")}</CardTitle>
            <span className="px-2 py-0.5 text-sm font-mono bg-teal-900/30 text-teal-400 rounded">
              VDOT {savedZones.vdot}
            </span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowCalculator(true)}
            className="text-gray-400 hover:text-white"
          >
            {t("card.recalculate")}
          </Button>
        </div>
        <CardDescription>
          {t("card.basedOnRace", {
            distance: savedZones.source_distance,
            time: savedZones.source_time_formatted,
          })}
        </CardDescription>
      </CardHeader>

      {/* Zones Display */}
      <div className="space-y-2 px-0">
        {compact ? (
          <PaceZonesCompact zones={savedZones.pace_zones} vdot={savedZones.vdot} />
        ) : (
          <div className="space-y-2">
            {ZONE_ORDER.map((key) => {
              const zone = savedZones.pace_zones[key];
              if (!zone) return null;

              const colors = ZONE_COLORS[key] || ZONE_COLORS.easy;

              return (
                <div
                  key={key}
                  className={clsx(
                    "p-3 rounded-lg border flex items-center justify-between",
                    colors.bg,
                    colors.border
                  )}
                >
                  <div className="flex items-center gap-2">
                    <div className={clsx("w-2 h-2 rounded-full", colors.bar)} />
                    <span className={clsx("font-medium", colors.text)}>
                      {zone.name}
                    </span>
                    <InfoTooltip
                      content={
                        <div className="w-[220px]">
                          <div className="font-semibold text-white mb-1">
                            {zone.name}
                          </div>
                          <div className="text-gray-300 text-sm">
                            {zone.description}
                          </div>
                          <div className="mt-2 text-xs text-gray-400">
                            Typical duration: {zone.typical_duration}
                          </div>
                        </div>
                      }
                      position="right"
                    />
                  </div>
                  <div className="text-right">
                    <span className="font-mono text-white">
                      {zone.max_pace_formatted} - {zone.min_pace_formatted}
                    </span>
                    <span className="text-gray-500 text-sm ml-1">/km</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Last Updated */}
      {savedZones.updated_at && (
        <div className="mt-4 pt-4 border-t border-gray-800 text-xs text-gray-500 text-center">
          {t("card.lastUpdated")}: {formatDate(savedZones.updated_at)}
        </div>
      )}
    </Card>
  );
}

export default PaceZonesCard;
