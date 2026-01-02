"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { clsx } from "clsx";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { InfoTooltip } from "@/components/ui/Tooltip";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

// Types for VDOT calculation
export interface PaceZone {
  name: string;
  min_pace_sec_per_km: number;
  max_pace_sec_per_km: number;
  min_pace_formatted: string;
  max_pace_formatted: string;
  pace_range_formatted: string;
  min_pace_per_mile: string;
  max_pace_per_mile: string;
  description: string;
  hr_range_min: number;
  hr_range_max: number;
  typical_duration: string;
}

export interface RacePrediction {
  distance: string;
  distance_km: number;
  time_sec: number;
  time_formatted: string;
  pace_sec_per_km: number;
  pace_formatted: string;
  pace_per_mile: string;
}

export interface VDOTResult {
  vdot: number;
  race_distance: string;
  race_time_sec: number;
  race_time_formatted: string;
  pace_zones: Record<string, PaceZone>;
  race_predictions: RacePrediction[];
}

// Race distance options
const RACE_DISTANCES = [
  { value: "5K", label: "5K", meters: 5000 },
  { value: "10K", label: "10K", meters: 10000 },
  { value: "half", label: "Half Marathon", meters: 21097.5 },
  { value: "marathon", label: "Marathon", meters: 42195 },
  { value: "custom", label: "Custom", meters: 0 },
];

interface VDOTCalculatorProps {
  onCalculate?: (result: VDOTResult) => void;
  onSave?: (result: VDOTResult) => void;
  savedVdot?: number | null;
  compact?: boolean;
}

export function VDOTCalculator({
  onCalculate,
  onSave,
  savedVdot,
  compact = false,
}: VDOTCalculatorProps) {
  const t = useTranslations("paceZones");

  // Form state
  const [distance, setDistance] = useState<string>("5K");
  const [customDistance, setCustomDistance] = useState<string>("");
  const [hours, setHours] = useState<string>("0");
  const [minutes, setMinutes] = useState<string>("");
  const [seconds, setSeconds] = useState<string>("");

  // Result state
  const [result, setResult] = useState<VDOTResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Parse time to seconds
  const getTimeInSeconds = useCallback((): number => {
    const h = parseInt(hours || "0", 10) || 0;
    const m = parseInt(minutes || "0", 10) || 0;
    const s = parseInt(seconds || "0", 10) || 0;
    return h * 3600 + m * 60 + s;
  }, [hours, minutes, seconds]);

  // Format time string for API
  const getTimeString = useCallback((): string => {
    const h = parseInt(hours || "0", 10) || 0;
    const m = parseInt(minutes || "0", 10) || 0;
    const s = parseInt(seconds || "0", 10) || 0;

    if (h > 0) {
      return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
    }
    return `${m}:${s.toString().padStart(2, "0")}`;
  }, [hours, minutes, seconds]);

  // Validate inputs
  const isValid = useCallback((): boolean => {
    const timeSeconds = getTimeInSeconds();
    if (timeSeconds <= 0) return false;

    if (distance === "custom") {
      const customDist = parseFloat(customDistance);
      if (isNaN(customDist) || customDist <= 0) return false;
    }

    return true;
  }, [distance, customDistance, getTimeInSeconds]);

  // Calculate VDOT
  const handleCalculate = async () => {
    if (!isValid()) {
      setError(t("errors.invalidInput"));
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const requestBody: {
        distance: string;
        time: string;
        custom_distance_m?: number;
      } = {
        distance,
        time: getTimeString(),
      };

      if (distance === "custom") {
        requestBody.custom_distance_m = parseFloat(customDistance) * 1000; // Convert km to meters
      }

      const response = await fetch("/api/v1/pace-zones/calculate-vdot", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || t("errors.calculationFailed"));
      }

      const data: VDOTResult = await response.json();
      setResult(data);
      onCalculate?.(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("errors.calculationFailed"));
    } finally {
      setIsLoading(false);
    }
  };

  // Save zones
  const handleSave = async () => {
    if (!result) return;

    try {
      const response = await fetch("/api/v1/pace-zones/my-zones", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({
          vdot: result.vdot,
          source_distance: result.race_distance,
          source_time_sec: result.race_time_sec,
        }),
      });

      if (!response.ok) {
        throw new Error(t("errors.saveFailed"));
      }

      onSave?.(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("errors.saveFailed"));
    }
  };

  return (
    <Card className={clsx(compact && "p-4")}>
      <CardHeader>
        <div className="flex items-center gap-2">
          <CardTitle>{t("calculator.title")}</CardTitle>
          <InfoTooltip
            content={
              <div className="w-[280px]">
                <div className="font-semibold text-white mb-1">
                  {t("calculator.vdotTitle")}
                </div>
                <div className="text-gray-300">{t("calculator.vdotDescription")}</div>
              </div>
            }
            position="right"
          />
        </div>
        <CardDescription>{t("calculator.subtitle")}</CardDescription>
      </CardHeader>

      <div className="space-y-4">
        {/* Race Distance Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            {t("calculator.distanceLabel")}
          </label>
          <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
            {RACE_DISTANCES.map((d) => (
              <button
                key={d.value}
                type="button"
                onClick={() => setDistance(d.value)}
                className={clsx(
                  "px-3 py-2 text-sm rounded-lg border transition-colors",
                  distance === d.value
                    ? "bg-teal-600 border-teal-500 text-white"
                    : "bg-gray-800 border-gray-700 text-gray-300 hover:border-gray-600"
                )}
              >
                {d.label}
              </button>
            ))}
          </div>
        </div>

        {/* Custom Distance Input */}
        {distance === "custom" && (
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              {t("calculator.customDistanceLabel")}
            </label>
            <div className="flex items-center gap-2">
              <Input
                type="number"
                value={customDistance}
                onChange={(e) => setCustomDistance(e.target.value)}
                placeholder="10.0"
                min="0.1"
                max="100"
                step="0.1"
                className="w-32"
              />
              <span className="text-gray-400">km</span>
            </div>
          </div>
        )}

        {/* Race Time Input */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            {t("calculator.timeLabel")}
          </label>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1">
              <Input
                type="number"
                value={hours}
                onChange={(e) => setHours(e.target.value)}
                placeholder="0"
                min="0"
                max="23"
                className="w-16 text-center"
              />
              <span className="text-gray-400">h</span>
            </div>
            <div className="flex items-center gap-1">
              <Input
                type="number"
                value={minutes}
                onChange={(e) => setMinutes(e.target.value)}
                placeholder="25"
                min="0"
                max="59"
                className="w-16 text-center"
              />
              <span className="text-gray-400">m</span>
            </div>
            <div className="flex items-center gap-1">
              <Input
                type="number"
                value={seconds}
                onChange={(e) => setSeconds(e.target.value)}
                placeholder="30"
                min="0"
                max="59"
                className="w-16 text-center"
              />
              <span className="text-gray-400">s</span>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="p-3 bg-red-900/20 border border-red-800 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Calculate Button */}
        <Button
          onClick={handleCalculate}
          disabled={!isValid() || isLoading}
          className="w-full"
        >
          {isLoading ? (
            <span className="flex items-center gap-2">
              <LoadingSpinner size="sm" />
              {t("calculator.calculating")}
            </span>
          ) : (
            t("calculator.calculateButton")
          )}
        </Button>

        {/* VDOT Result Display */}
        {result && (
          <div className="mt-6 space-y-4">
            {/* VDOT Score */}
            <div className="flex items-center justify-between p-4 bg-gradient-to-r from-teal-900/40 to-teal-800/20 rounded-lg border border-teal-700/30">
              <div>
                <div className="text-sm text-gray-400">{t("calculator.yourVdot")}</div>
                <div className="text-3xl font-bold text-teal-400">{result.vdot}</div>
              </div>
              <div className="text-right">
                <div className="text-sm text-gray-400">{result.race_distance}</div>
                <div className="text-lg font-mono text-white">
                  {result.race_time_formatted}
                </div>
              </div>
            </div>

            {/* Saved VDOT comparison */}
            {savedVdot && savedVdot !== result.vdot && (
              <div className="text-sm text-gray-400 flex items-center gap-2">
                <span>{t("calculator.currentSaved")}:</span>
                <span className="font-mono text-white">{savedVdot}</span>
                {result.vdot > savedVdot && (
                  <span className="text-green-400">
                    (+{(result.vdot - savedVdot).toFixed(1)})
                  </span>
                )}
                {result.vdot < savedVdot && (
                  <span className="text-orange-400">
                    ({(result.vdot - savedVdot).toFixed(1)})
                  </span>
                )}
              </div>
            )}

            {/* Save Button */}
            <Button onClick={handleSave} variant="secondary" className="w-full">
              {t("calculator.saveZones")}
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}

export default VDOTCalculator;
