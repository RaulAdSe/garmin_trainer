"use client";

import { useMemo } from "react";

interface HRZone {
  zone: number;
  name: string;
  min: number;
  max: number;
  color: string;
}

interface HRZonesBadgeProps {
  zones: {
    z1: [number, number];
    z2: [number, number];
    z3: [number, number];
    z4: [number, number];
    z5: [number, number];
  };
  currentHR?: number;
  showLabels?: boolean;
  compact?: boolean;
}

const ZONE_COLORS = [
  "bg-blue-500",    // Z1 - Recovery
  "bg-green-500",   // Z2 - Aerobic
  "bg-yellow-500",  // Z3 - Tempo
  "bg-orange-500",  // Z4 - Threshold
  "bg-red-500",     // Z5 - VO2max
];

const ZONE_NAMES = [
  "Recovery",
  "Aerobic",
  "Tempo",
  "Threshold",
  "VO2max",
];

export function HRZonesBadge({
  zones,
  currentHR,
  showLabels = true,
  compact = false,
}: HRZonesBadgeProps) {
  const zoneData: HRZone[] = useMemo(() => {
    const zoneArray = [zones.z1, zones.z2, zones.z3, zones.z4, zones.z5];
    return zoneArray.map((range, index) => ({
      zone: index + 1,
      name: ZONE_NAMES[index],
      min: range[0],
      max: range[1],
      color: ZONE_COLORS[index],
    }));
  }, [zones]);

  const currentZone = useMemo(() => {
    if (!currentHR) return null;
    for (const zone of zoneData) {
      if (currentHR >= zone.min && currentHR <= zone.max) {
        return zone;
      }
    }
    return null;
  }, [currentHR, zoneData]);

  if (compact) {
    return (
      <div className="flex items-center gap-1">
        {zoneData.map((zone) => (
          <div
            key={zone.zone}
            className={`h-2 w-4 rounded-sm ${zone.color} ${
              currentZone?.zone === zone.zone
                ? "ring-2 ring-white"
                : "opacity-60"
            }`}
            title={`Z${zone.zone} ${zone.name}: ${zone.min}-${zone.max} bpm`}
          />
        ))}
        {currentHR && (
          <span className="ml-2 text-sm font-mono text-gray-300">
            {currentHR} bpm
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Zone bars */}
      <div className="flex gap-1">
        {zoneData.map((zone) => {
          const isActive = currentZone?.zone === zone.zone;
          const width = ((zone.max - zone.min) / (zones.z5[1] - zones.z1[0])) * 100;

          return (
            <div
              key={zone.zone}
              className={`relative ${zone.color} rounded-sm transition-all ${
                isActive ? "ring-2 ring-white scale-105" : "opacity-70"
              }`}
              style={{ width: `${Math.max(width, 15)}%`, height: "24px" }}
              title={`Z${zone.zone} ${zone.name}: ${zone.min}-${zone.max} bpm`}
            >
              <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-white/90">
                Z{zone.zone}
              </span>
            </div>
          );
        })}
      </div>

      {/* Labels */}
      {showLabels && (
        <div className="flex justify-between text-xs text-gray-400">
          <span>{zones.z1[0]} bpm</span>
          <span>{zones.z5[1]} bpm</span>
        </div>
      )}

      {/* Current HR indicator */}
      {currentHR && currentZone && (
        <div
          className={`text-center text-sm font-medium ${currentZone.color.replace(
            "bg-",
            "text-"
          )}`}
        >
          Current: {currentHR} bpm (Zone {currentZone.zone} - {currentZone.name})
        </div>
      )}

      {/* Zone legend */}
      {showLabels && (
        <div className="grid grid-cols-5 gap-1 text-xs">
          {zoneData.map((zone) => (
            <div key={zone.zone} className="text-center">
              <div
                className={`h-1 w-full rounded-full ${zone.color} opacity-60 mb-1`}
              />
              <div className="text-gray-400">{zone.name}</div>
              <div className="text-gray-500 font-mono">
                {zone.min}-{zone.max}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Compact badge for inline display
export function HRZoneBadgeInline({
  zone,
  value,
}: {
  zone: number;
  value?: number;
}) {
  const color = ZONE_COLORS[zone - 1] || ZONE_COLORS[0];
  const name = ZONE_NAMES[zone - 1] || "Unknown";

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium text-white ${color}`}
    >
      Z{zone}
      {value && <span className="font-mono">{value}bpm</span>}
    </span>
  );
}
