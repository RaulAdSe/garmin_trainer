"use client";

import { cn } from "@/lib/utils";
import { InfoTooltip } from "@/components/ui/Tooltip";
import { Card } from "@/components/ui/Card";

interface TrainingBalanceProps {
  ctl: number;
  atl: number;
  className?: string;
  style?: React.CSSProperties;
}

export function TrainingBalance({ ctl, atl, className, style }: TrainingBalanceProps) {
  // Normalize to a reasonable scale (0-100 for most athletes)
  const maxScale = Math.max(ctl, atl, 80);
  const ctlWidth = (ctl / maxScale) * 100;
  const atlWidth = (atl / maxScale) * 100;

  return (
    <Card className={cn("animate-slideUp", className)} style={style}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">
          Training Balance
        </h3>
        <InfoTooltip
          content={
            <div className="w-[260px]">
              <div className="font-semibold text-white mb-1">CTL vs ATL</div>
              <div className="text-gray-300 text-xs space-y-1">
                <p><span className="text-teal-400">Fitness (CTL)</span>: 42-day training load average</p>
                <p><span className="text-orange-400">Fatigue (ATL)</span>: 7-day training load average</p>
                <p>Balance between these determines your form.</p>
              </div>
            </div>
          }
          position="top"
        />
      </div>

      <div className="space-y-3">
        {/* CTL - Fitness */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-400">Fitness (CTL)</span>
            <span className="font-mono font-bold text-teal-400">{ctl.toFixed(0)}</span>
          </div>
          <div className="h-3 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-teal-600 to-teal-400 transition-all duration-700 ease-out"
              style={{ width: `${ctlWidth}%` }}
            >
              <div className="h-full bg-gradient-to-r from-transparent via-white/10 to-transparent" />
            </div>
          </div>
        </div>

        {/* ATL - Fatigue */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-400">Fatigue (ATL)</span>
            <span className="font-mono font-bold text-orange-400">{atl.toFixed(0)}</span>
          </div>
          <div className="h-3 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-orange-600 to-orange-400 transition-all duration-700 ease-out"
              style={{ width: `${atlWidth}%` }}
            >
              <div className="h-full bg-gradient-to-r from-transparent via-white/10 to-transparent" />
            </div>
          </div>
        </div>
      </div>

      {/* Balance indicator */}
      <div className="mt-4 pt-3 border-t border-gray-800">
        <div className="flex items-center justify-center gap-3">
          <BalanceIndicator ctl={ctl} atl={atl} />
        </div>
      </div>
    </Card>
  );
}

// Visual balance indicator
function BalanceIndicator({ ctl, atl }: { ctl: number; atl: number }) {
  const ratio = atl > 0 ? ctl / atl : 1;

  let status: { label: string; color: string; description: string };

  if (ratio >= 1.3) {
    status = { label: "Well Rested", color: "text-green-400", description: "Fitness ahead of fatigue" };
  } else if (ratio >= 1.0) {
    status = { label: "Balanced", color: "text-teal-400", description: "Good training equilibrium" };
  } else if (ratio >= 0.8) {
    status = { label: "Building", color: "text-yellow-400", description: "Fatigue accumulating" };
  } else {
    status = { label: "Overreaching", color: "text-orange-400", description: "Consider recovery" };
  }

  return (
    <div className="text-center">
      <span className={cn("text-sm font-medium", status.color)}>
        {status.label}
      </span>
      <span className="text-xs text-gray-500 ml-2">
        {status.description}
      </span>
    </div>
  );
}

// Skeleton loader
export function TrainingBalanceSkeleton() {
  return (
    <Card className="animate-pulse">
      <div className="flex justify-between mb-4">
        <div className="w-28 h-4 bg-gray-800 rounded" />
        <div className="w-4 h-4 bg-gray-800 rounded-full" />
      </div>
      <div className="space-y-3">
        <div className="space-y-1.5">
          <div className="flex justify-between">
            <div className="w-20 h-4 bg-gray-800 rounded" />
            <div className="w-10 h-4 bg-gray-800 rounded" />
          </div>
          <div className="h-3 bg-gray-800 rounded-full" />
        </div>
        <div className="space-y-1.5">
          <div className="flex justify-between">
            <div className="w-20 h-4 bg-gray-800 rounded" />
            <div className="w-10 h-4 bg-gray-800 rounded" />
          </div>
          <div className="h-3 bg-gray-800 rounded-full" />
        </div>
      </div>
      <div className="mt-4 pt-3 border-t border-gray-800">
        <div className="w-32 h-4 bg-gray-800 rounded mx-auto" />
      </div>
    </Card>
  );
}
