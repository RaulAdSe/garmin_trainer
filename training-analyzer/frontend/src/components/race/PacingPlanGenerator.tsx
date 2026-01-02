'use client';

import React, { useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { Card, Button, LoadingSpinner } from '@/components/ui';
import {
  useGeneratePacingPlan,
  useAvailableStrategies,
  getTimeComponents,
} from '@/hooks/useRacePacing';
import type {
  RaceDistance,
  PacingStrategy,
  WeatherConditions,
  CourseProfile,
  GeneratePacingPlanRequest,
  PacingPlan,
} from '@/lib/types';
import { RACE_DISTANCES_KM, STRATEGY_NAMES } from '@/lib/types';
import SplitTable from './SplitTable';
import WeatherAdjustments from './WeatherAdjustments';
import ElevationPaceChart from './ElevationPaceChart';

interface PacingPlanGeneratorProps {
  onPlanGenerated?: (plan: PacingPlan) => void;
  initialDistance?: RaceDistance;
  initialTargetTime?: number; // in seconds
}

export default function PacingPlanGenerator({
  onPlanGenerated,
  initialDistance = 'half_marathon',
  initialTargetTime,
}: PacingPlanGeneratorProps) {
  const t = useTranslations('racePacing');

  // Form state
  const [raceDistance, setRaceDistance] = useState<RaceDistance>(initialDistance);
  const [customDistanceKm, setCustomDistanceKm] = useState<number>(10);
  const [targetHours, setTargetHours] = useState<number>(
    initialTargetTime ? getTimeComponents(initialTargetTime).hours : 1
  );
  const [targetMinutes, setTargetMinutes] = useState<number>(
    initialTargetTime ? getTimeComponents(initialTargetTime).minutes : 45
  );
  const [targetSeconds, setTargetSeconds] = useState<number>(
    initialTargetTime ? getTimeComponents(initialTargetTime).seconds : 0
  );
  const [raceName, setRaceName] = useState<string>('');
  const [strategy, setStrategy] = useState<PacingStrategy | ''>('');

  // Weather conditions (optional)
  const [showWeather, setShowWeather] = useState(false);
  const [temperature, setTemperature] = useState<number>(15);
  const [humidity, setHumidity] = useState<number>(60);
  const [windSpeed, setWindSpeed] = useState<number>(0);
  const [windDirection, setWindDirection] = useState<'headwind' | 'tailwind' | 'crosswind' | 'variable'>('variable');
  const [altitude, setAltitude] = useState<number>(0);

  // Generated plan
  const [generatedPlan, setGeneratedPlan] = useState<PacingPlan | null>(null);

  // Hooks
  const { data: strategiesData, isLoading: loadingStrategies } = useAvailableStrategies();
  const generatePlan = useGeneratePacingPlan();

  const handleGenerate = useCallback(() => {
    const distanceKm =
      raceDistance === 'custom' ? customDistanceKm : RACE_DISTANCES_KM[raceDistance];

    if (!distanceKm) return;

    const targetTimeSec = targetHours * 3600 + targetMinutes * 60 + targetSeconds;
    if (targetTimeSec <= 0) return;

    const request: GeneratePacingPlanRequest = {
      target_time_sec: targetTimeSec,
      race_distance: raceDistance,
      distance_km: raceDistance === 'custom' ? customDistanceKm : undefined,
      race_name: raceName || undefined,
      strategy: strategy || undefined,
    };

    // Add weather if enabled
    if (showWeather) {
      request.weather_conditions = {
        temperature_c: temperature,
        humidity_pct: humidity,
        wind_speed_kmh: windSpeed,
        wind_direction: windDirection,
        altitude_m: altitude,
      };
    }

    generatePlan.mutate(request, {
      onSuccess: (plan) => {
        setGeneratedPlan(plan);
        onPlanGenerated?.(plan);
      },
    });
  }, [
    raceDistance,
    customDistanceKm,
    targetHours,
    targetMinutes,
    targetSeconds,
    raceName,
    strategy,
    showWeather,
    temperature,
    humidity,
    windSpeed,
    windDirection,
    altitude,
    generatePlan,
    onPlanGenerated,
  ]);

  return (
    <div className="space-y-6">
      {/* Generator Form */}
      <Card className="p-6">
        <h2 className="text-lg font-semibold text-white mb-4">{t('title')}</h2>
        <p className="text-gray-400 text-sm mb-6">{t('subtitle')}</p>

        <div className="space-y-4">
          {/* Race Distance */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              {t('raceDistance')}
            </label>
            <select
              value={raceDistance}
              onChange={(e) => setRaceDistance(e.target.value as RaceDistance)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-orange-500 focus:border-transparent"
            >
              <option value="5K">{t('distances.5K')}</option>
              <option value="10K">{t('distances.10K')}</option>
              <option value="half_marathon">{t('distances.halfMarathon')}</option>
              <option value="marathon">{t('distances.marathon')}</option>
              <option value="custom">{t('distances.custom')}</option>
            </select>
          </div>

          {/* Custom Distance */}
          {raceDistance === 'custom' && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                {t('customDistance')}
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  value={customDistanceKm}
                  onChange={(e) => setCustomDistanceKm(parseFloat(e.target.value) || 0)}
                  min={0.5}
                  max={200}
                  step={0.5}
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-orange-500"
                />
                <span className="text-gray-400">km</span>
              </div>
            </div>
          )}

          {/* Target Time */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              {t('targetTime')}
            </label>
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1">
                <input
                  type="number"
                  value={targetHours}
                  onChange={(e) => setTargetHours(parseInt(e.target.value) || 0)}
                  min={0}
                  max={24}
                  className="w-16 bg-gray-800 border border-gray-700 rounded-lg px-2 py-2 text-white text-center focus:ring-2 focus:ring-orange-500"
                />
                <span className="text-gray-400">h</span>
              </div>
              <span className="text-gray-400">:</span>
              <div className="flex items-center gap-1">
                <input
                  type="number"
                  value={targetMinutes}
                  onChange={(e) => setTargetMinutes(parseInt(e.target.value) || 0)}
                  min={0}
                  max={59}
                  className="w-16 bg-gray-800 border border-gray-700 rounded-lg px-2 py-2 text-white text-center focus:ring-2 focus:ring-orange-500"
                />
                <span className="text-gray-400">m</span>
              </div>
              <span className="text-gray-400">:</span>
              <div className="flex items-center gap-1">
                <input
                  type="number"
                  value={targetSeconds}
                  onChange={(e) => setTargetSeconds(parseInt(e.target.value) || 0)}
                  min={0}
                  max={59}
                  className="w-16 bg-gray-800 border border-gray-700 rounded-lg px-2 py-2 text-white text-center focus:ring-2 focus:ring-orange-500"
                />
                <span className="text-gray-400">s</span>
              </div>
            </div>
          </div>

          {/* Race Name (Optional) */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              {t('raceName')} <span className="text-gray-500">({t('optional')})</span>
            </label>
            <input
              type="text"
              value={raceName}
              onChange={(e) => setRaceName(e.target.value)}
              placeholder={t('raceNamePlaceholder')}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:ring-2 focus:ring-orange-500"
            />
          </div>

          {/* Pacing Strategy */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              {t('pacingStrategy')}
            </label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value as PacingStrategy | '')}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-orange-500"
            >
              <option value="">{t('autoSelectStrategy')}</option>
              <option value="even">{t('strategies.even')}</option>
              <option value="negative_split">{t('strategies.negativeSplit')}</option>
              <option value="positive_split">{t('strategies.positiveSplit')}</option>
              <option value="course_specific">{t('strategies.courseSpecific')}</option>
            </select>
            {!strategy && (
              <p className="text-xs text-gray-500 mt-1">{t('autoSelectHint')}</p>
            )}
          </div>

          {/* Weather Conditions Toggle */}
          <div className="border-t border-gray-700 pt-4">
            <button
              type="button"
              onClick={() => setShowWeather(!showWeather)}
              className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
            >
              <svg
                className={`w-4 h-4 transition-transform ${showWeather ? 'rotate-90' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
              {t('addWeatherConditions')}
            </button>

            {showWeather && (
              <div className="mt-4 space-y-4 p-4 bg-gray-800/50 rounded-lg">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      {t('weather.temperature')}
                    </label>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        value={temperature}
                        onChange={(e) => setTemperature(parseInt(e.target.value) || 0)}
                        min={-30}
                        max={50}
                        className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-1 text-white text-sm"
                      />
                      <span className="text-gray-400 text-sm">C</span>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      {t('weather.humidity')}
                    </label>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        value={humidity}
                        onChange={(e) => setHumidity(parseInt(e.target.value) || 0)}
                        min={0}
                        max={100}
                        className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-1 text-white text-sm"
                      />
                      <span className="text-gray-400 text-sm">%</span>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      {t('weather.windSpeed')}
                    </label>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        value={windSpeed}
                        onChange={(e) => setWindSpeed(parseInt(e.target.value) || 0)}
                        min={0}
                        max={100}
                        className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-1 text-white text-sm"
                      />
                      <span className="text-gray-400 text-sm">km/h</span>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      {t('weather.windDirection')}
                    </label>
                    <select
                      value={windDirection}
                      onChange={(e) =>
                        setWindDirection(
                          e.target.value as 'headwind' | 'tailwind' | 'crosswind' | 'variable'
                        )
                      }
                      className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-1 text-white text-sm"
                    >
                      <option value="variable">{t('weather.directions.variable')}</option>
                      <option value="headwind">{t('weather.directions.headwind')}</option>
                      <option value="tailwind">{t('weather.directions.tailwind')}</option>
                      <option value="crosswind">{t('weather.directions.crosswind')}</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      {t('weather.altitude')}
                    </label>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        value={altitude}
                        onChange={(e) => setAltitude(parseInt(e.target.value) || 0)}
                        min={0}
                        max={5000}
                        className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-1 text-white text-sm"
                      />
                      <span className="text-gray-400 text-sm">m</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Generate Button */}
          <Button
            onClick={handleGenerate}
            disabled={generatePlan.isPending}
            className="w-full"
          >
            {generatePlan.isPending ? (
              <div className="flex items-center justify-center gap-2">
                <LoadingSpinner size="sm" />
                {t('generating')}
              </div>
            ) : (
              t('generatePlan')
            )}
          </Button>

          {/* Error */}
          {generatePlan.isError && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
              {t('errorGenerating')}
            </div>
          )}
        </div>
      </Card>

      {/* Generated Plan Results */}
      {generatedPlan && (
        <div className="space-y-6">
          {/* Plan Summary */}
          <Card className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-white">
                  {generatedPlan.race_name || t('yourPacingPlan')}
                </h3>
                <p className="text-gray-400 text-sm">
                  {generatedPlan.distance_km.toFixed(2)} km | {generatedPlan.target_time_formatted}
                </p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-orange-500">
                  {generatedPlan.base_pace_formatted}/km
                </div>
                <div className="text-sm text-gray-400">{t('targetPace')}</div>
              </div>
            </div>

            {/* Strategy Info */}
            {generatedPlan.strategy_recommendation && (
              <div className="p-3 bg-gray-800/50 rounded-lg mb-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-white">
                    {STRATEGY_NAMES[generatedPlan.strategy]}
                  </span>
                  <span className="text-xs text-gray-500">
                    ({Math.round(generatedPlan.strategy_recommendation.confidence * 100)}%{' '}
                    {t('confidence')})
                  </span>
                </div>
                <p className="text-xs text-gray-400">
                  {generatedPlan.strategy_recommendation.reasoning}
                </p>
              </div>
            )}

            {/* Tips */}
            {generatedPlan.tips.length > 0 && (
              <div className="border-t border-gray-700 pt-4">
                <h4 className="text-sm font-medium text-gray-300 mb-2">{t('raceTips')}</h4>
                <ul className="space-y-1">
                  {generatedPlan.tips.map((tip, index) => (
                    <li key={index} className="text-sm text-gray-400 flex items-start gap-2">
                      <span className="text-orange-500 mt-1">*</span>
                      {tip}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Card>

          {/* Weather Adjustments */}
          {generatedPlan.weather_adjustment && generatedPlan.weather_conditions && (
            <WeatherAdjustments
              conditions={generatedPlan.weather_conditions}
              adjustment={generatedPlan.weather_adjustment}
            />
          )}

          {/* Elevation Chart */}
          {generatedPlan.course_profile &&
            generatedPlan.course_profile.elevation_points.length > 0 && (
              <ElevationPaceChart plan={generatedPlan} />
            )}

          {/* Split Table */}
          <SplitTable splits={generatedPlan.splits} />
        </div>
      )}
    </div>
  );
}
