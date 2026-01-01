"use client";

import { useTranslations } from "next-intl";
import { useAthleteContext } from "@/hooks/useAthleteContext";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { InfoTooltip } from "@/components/ui/Tooltip";
import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { clsx } from "clsx";

export default function ZonesPage() {
  const t = useTranslations("zones");
  const { data: context, isLoading, error, refetch } = useAthleteContext();

  if (isLoading) {
    return (
      <div className="space-y-6">
        {/* Header skeleton */}
        <div className="animate-fadeIn">
          <div className="h-8 w-48 skeleton rounded mb-2" />
          <div className="h-5 w-64 skeleton rounded" />
        </div>

        {/* Cards skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-8">
        <ErrorState
          title={t("errorLoading")}
          message={error.message}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="animate-fadeIn">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-100">
          {t("title")}
        </h1>
        <p className="text-sm sm:text-base text-gray-400 mt-1">
          {t("subtitle")}
        </p>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* Training Paces Card */}
        <Card className="animate-slideUp">
          <CardHeader>
            <div className="flex items-center gap-2">
              <CardTitle>{t("trainingPaces.title")}</CardTitle>
              <InfoTooltip
                content={<div className="w-[280px] text-sm">{t("trainingPaces.tooltip")}</div>}
                position="top"
              />
            </div>
            <CardDescription>{t("trainingPaces.description")}</CardDescription>
          </CardHeader>

          {context?.training_paces && context.training_paces.length > 0 ? (
            <div className="space-y-1 sm:space-y-2">
              {context.training_paces.map((pace, index) => (
                <div
                  key={pace.name}
                  className="flex justify-between items-center py-2 sm:py-2.5 px-2 sm:px-3 -mx-2 sm:-mx-3 rounded-lg hover:bg-gray-800/50 transition-colors animate-slideUp"
                  style={{ animationDelay: `${index * 0.05}s` }}
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-100 text-sm sm:text-base">
                        {pace.name}
                      </span>
                      <InfoTooltip
                        content={<div className="w-[240px] text-sm">{pace.description}</div>}
                        position="top"
                      />
                    </div>
                    <span className="text-gray-500 text-xs sm:text-sm block sm:hidden mt-0.5">
                      {pace.hr_zone}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 ml-2">
                    <span className="text-gray-500 text-xs sm:text-sm hidden sm:inline shrink-0">
                      {pace.hr_zone}
                    </span>
                    <span className="text-teal-400 font-mono text-sm sm:text-base shrink-0 font-semibold">
                      {pace.pace_formatted}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 sm:py-12">
              <div className="text-4xl sm:text-5xl mb-3 sm:mb-4">🎯</div>
              <p className="text-gray-500 text-sm sm:text-base">
                {t("trainingPaces.noPaces")}
              </p>
            </div>
          )}
        </Card>

        {/* HR Zones Card */}
        <Card className="animate-slideUp" style={{ animationDelay: "0.1s" }}>
          <CardHeader>
            <div className="flex items-center gap-2">
              <CardTitle>{t("hrZones.title")}</CardTitle>
              <InfoTooltip
                content={<div className="w-[280px] text-sm">{t("hrZones.tooltip")}</div>}
                position="top"
              />
            </div>
            <CardDescription>{t("hrZones.description")}</CardDescription>
          </CardHeader>

          {context?.hr_zones && context.hr_zones.length > 0 ? (
            <div className="space-y-3 sm:space-y-4">
              {context.hr_zones.map((zone, index) => (
                <div
                  key={zone.zone}
                  className="animate-slideUp"
                  style={{ animationDelay: `${(index + 2) * 0.05}s` }}
                >
                  {/* Zone Header */}
                  <div className="flex justify-between items-center mb-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={clsx(
                          "font-bold text-sm sm:text-base",
                          getZoneColor(zone.zone)
                        )}
                      >
                        Z{zone.zone}
                      </span>
                      <span className="text-gray-300 text-sm sm:text-base font-medium">
                        {zone.name}
                      </span>
                      <InfoTooltip
                        content={<div className="w-[240px] text-sm">{zone.description}</div>}
                        position="top"
                      />
                    </div>
                    <span className="font-mono text-gray-400 text-xs sm:text-sm shrink-0">
                      {zone.min_hr}-{zone.max_hr} bpm
                    </span>
                  </div>

                  {/* Visual Bar */}
                  <div className="relative h-3 sm:h-4 bg-gray-800 rounded-full overflow-hidden">
                    {/* Full range background */}
                    <div className="absolute inset-0 flex">
                      {/* Calculate the position of this zone in the overall HR range */}
                      {context.hr_zones && (() => {
                        const minHR = Math.min(...context.hr_zones.map(z => z.min_hr));
                        const maxHR = Math.max(...context.hr_zones.map(z => z.max_hr));
                        const range = maxHR - minHR;
                        const zoneStart = ((zone.min_hr - minHR) / range) * 100;
                        const zoneWidth = ((zone.max_hr - zone.min_hr) / range) * 100;

                        return (
                          <div
                            className={clsx(
                              "absolute h-full rounded-full transition-all duration-500",
                              getZoneGradient(zone.zone)
                            )}
                            style={{
                              left: `${zoneStart}%`,
                              width: `${zoneWidth}%`,
                            }}
                          />
                        );
                      })()}
                    </div>
                  </div>
                </div>
              ))}

              {/* HR Legend */}
              {context.hr_zones && context.hr_zones.length > 0 && (
                <div className="flex justify-between items-center pt-2 text-xs text-gray-500 border-t border-gray-800">
                  <span>{Math.min(...context.hr_zones.map(z => z.min_hr))} bpm</span>
                  <span className="text-gray-600">
                    {t("hrZones.range")}
                  </span>
                  <span>{Math.max(...context.hr_zones.map(z => z.max_hr))} bpm</span>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 sm:py-12">
              <div className="text-4xl sm:text-5xl mb-3 sm:mb-4">❤️</div>
              <p className="text-gray-500 text-sm sm:text-base">
                {t("hrZones.noZones")}
              </p>
            </div>
          )}
        </Card>
      </div>

      {/* Additional Info Card */}
      {context?.physiology && (
        <Card className="animate-slideUp" style={{ animationDelay: "0.2s" }}>
          <CardHeader>
            <div className="flex items-center gap-2">
              <CardTitle>{t("physiology.title")}</CardTitle>
              <InfoTooltip
                content={<div className="w-[280px] text-sm">{t("physiology.tooltip")}</div>}
                position="top"
              />
            </div>
            <CardDescription>{t("physiology.description")}</CardDescription>
          </CardHeader>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {/* Max HR */}
            <div className="text-center p-3 sm:p-4 rounded-lg bg-gray-800/50">
              <div className="text-2xl sm:text-3xl font-bold text-red-400 mb-1">
                {context.physiology.max_hr}
              </div>
              <div className="text-xs sm:text-sm text-gray-400">
                {t("physiology.maxHr")}
              </div>
            </div>

            {/* LTHR */}
            <div className="text-center p-3 sm:p-4 rounded-lg bg-gray-800/50">
              <div className="text-2xl sm:text-3xl font-bold text-orange-400 mb-1">
                {context.physiology.lthr}
              </div>
              <div className="text-xs sm:text-sm text-gray-400">
                {t("physiology.lthr")}
              </div>
            </div>

            {/* Rest HR */}
            <div className="text-center p-3 sm:p-4 rounded-lg bg-gray-800/50">
              <div className="text-2xl sm:text-3xl font-bold text-blue-400 mb-1">
                {context.physiology.rest_hr}
              </div>
              <div className="text-xs sm:text-sm text-gray-400">
                {t("physiology.restHr")}
              </div>
            </div>

            {/* VDOT (if available) */}
            {context.physiology.vdot && (
              <div className="text-center p-3 sm:p-4 rounded-lg bg-gray-800/50">
                <div className="text-2xl sm:text-3xl font-bold text-teal-400 mb-1">
                  {context.physiology.vdot.toFixed(1)}
                </div>
                <div className="text-xs sm:text-sm text-gray-400 flex items-center justify-center gap-1">
                  {t("physiology.vdot")}
                  <InfoTooltip
                    content={<div className="w-[240px] text-sm">{t("physiology.vdotTooltip")}</div>}
                    position="top"
                  />
                </div>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}

// Helper function to get zone color
function getZoneColor(zone: number): string {
  const colors: Record<number, string> = {
    1: "text-blue-400",
    2: "text-green-400",
    3: "text-yellow-400",
    4: "text-orange-400",
    5: "text-red-400",
  };
  return colors[zone] || "text-gray-400";
}

// Helper function to get zone gradient
function getZoneGradient(zone: number): string {
  const gradients: Record<number, string> = {
    1: "bg-gradient-to-r from-blue-600/60 to-blue-500/60",
    2: "bg-gradient-to-r from-green-600/60 to-green-500/60",
    3: "bg-gradient-to-r from-yellow-600/60 to-yellow-500/60",
    4: "bg-gradient-to-r from-orange-600/60 to-orange-500/60",
    5: "bg-gradient-to-r from-red-600/60 to-red-500/60",
  };
  return gradients[zone] || "bg-gray-600/60";
}
