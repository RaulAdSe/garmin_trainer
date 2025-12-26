"use client";

import { clsx } from "clsx";

interface ReadinessGaugeProps {
  score: number;
  zone: "green" | "yellow" | "red" | string;
  recommendation: string;
}

export function ReadinessGauge({
  score,
  zone,
  recommendation,
}: ReadinessGaugeProps) {
  const zoneColors = {
    green: {
      bg: "bg-green-500",
      text: "text-green-400",
      label: "Ready for Quality",
      description: "Your body is well-recovered and ready for hard training.",
    },
    yellow: {
      bg: "bg-yellow-500",
      text: "text-yellow-400",
      label: "Moderate Training",
      description: "Some fatigue present. Consider moderate intensity today.",
    },
    red: {
      bg: "bg-red-500",
      text: "text-red-400",
      label: "Recovery Focus",
      description: "High fatigue detected. Prioritize rest or easy activity.",
    },
  };

  const config = zoneColors[zone as keyof typeof zoneColors] || zoneColors.yellow;

  // Calculate the rotation for the gauge needle (-90 to 90 degrees)
  const rotation = -90 + (score / 100) * 180;

  return (
    <div className="flex flex-col items-center">
      {/* Gauge */}
      <div className="relative w-48 h-24 mb-4">
        {/* Background arc */}
        <svg className="w-full h-full" viewBox="0 0 100 50">
          {/* Red zone (0-33) */}
          <path
            d="M 5 50 A 45 45 0 0 1 20.7 15.9"
            fill="none"
            stroke="#dc2626"
            strokeWidth="8"
            strokeLinecap="round"
          />
          {/* Yellow zone (33-67) */}
          <path
            d="M 20.7 15.9 A 45 45 0 0 1 79.3 15.9"
            fill="none"
            stroke="#eab308"
            strokeWidth="8"
            strokeLinecap="round"
          />
          {/* Green zone (67-100) */}
          <path
            d="M 79.3 15.9 A 45 45 0 0 1 95 50"
            fill="none"
            stroke="#22c55e"
            strokeWidth="8"
            strokeLinecap="round"
          />
        </svg>

        {/* Needle */}
        <div
          className="absolute bottom-0 left-1/2 w-1 h-20 bg-white origin-bottom rounded-full transition-transform duration-500"
          style={{ transform: `translateX(-50%) rotate(${rotation}deg)` }}
        />

        {/* Center circle */}
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-4 h-4 bg-gray-700 rounded-full border-2 border-white" />
      </div>

      {/* Score */}
      <div className="text-center">
        <div className={clsx("text-5xl font-bold", config.text)}>{Math.round(score)}</div>
        <div className="text-sm text-gray-400 mb-2">out of 100</div>
        <div className={clsx("text-lg font-semibold", config.text)}>
          {config.label}
        </div>
        <p className="text-gray-400 text-sm mt-2 max-w-md">
          {recommendation || config.description}
        </p>
      </div>
    </div>
  );
}
