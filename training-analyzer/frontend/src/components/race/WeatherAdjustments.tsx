'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui';
import type { WeatherConditions, WeatherAdjustment } from '@/lib/types';

interface WeatherAdjustmentsProps {
  conditions: WeatherConditions;
  adjustment: WeatherAdjustment;
}

export default function WeatherAdjustments({
  conditions,
  adjustment,
}: WeatherAdjustmentsProps) {
  const t = useTranslations('racePacing.weather');

  const formatAdjustment = (value: number): string => {
    const pct = value.toFixed(1);
    return value >= 0 ? `+${pct}%` : `${pct}%`;
  };

  const getImpactColor = (value: number): string => {
    if (value <= 0) return 'text-green-400';
    if (value <= 2) return 'text-yellow-400';
    if (value <= 5) return 'text-orange-400';
    return 'text-red-400';
  };

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold text-white mb-4">{t('adjustments')}</h3>

      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Temperature */}
        <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707" />
            </svg>
            <span className="text-sm text-gray-300">{conditions.temperature_c}°C</span>
          </div>
          <span className={`text-sm font-medium ${getImpactColor(adjustment.temperature_adjustment_pct)}`}>
            {formatAdjustment(adjustment.temperature_adjustment_pct)}
          </span>
        </div>

        {/* Humidity */}
        <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
            </svg>
            <span className="text-sm text-gray-300">{conditions.humidity_pct}%</span>
          </div>
          <span className={`text-sm font-medium ${getImpactColor(adjustment.humidity_adjustment_pct)}`}>
            {formatAdjustment(adjustment.humidity_adjustment_pct)}
          </span>
        </div>

        {/* Wind */}
        {conditions.wind_speed_kmh > 0 && (
          <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
              <span className="text-sm text-gray-300">
                {conditions.wind_speed_kmh} km/h {conditions.wind_direction}
              </span>
            </div>
            <span className={`text-sm font-medium ${getImpactColor(adjustment.wind_adjustment_pct)}`}>
              {formatAdjustment(adjustment.wind_adjustment_pct)}
            </span>
          </div>
        )}

        {/* Altitude */}
        {conditions.altitude_m > 0 && (
          <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
              </svg>
              <span className="text-sm text-gray-300">{conditions.altitude_m}m</span>
            </div>
            <span className={`text-sm font-medium ${getImpactColor(adjustment.altitude_adjustment_pct)}`}>
              {formatAdjustment(adjustment.altitude_adjustment_pct)}
            </span>
          </div>
        )}
      </div>

      {/* Total Impact */}
      <div className="border-t border-gray-700 pt-4">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-sm font-medium text-white">{t('totalImpact')}</span>
            <p className="text-xs text-gray-500">{t('totalImpactHint')}</p>
          </div>
          <div className="text-right">
            <span className={`text-lg font-bold ${getImpactColor(adjustment.total_adjustment_pct)}`}>
              {formatAdjustment(adjustment.total_adjustment_pct)}
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}
