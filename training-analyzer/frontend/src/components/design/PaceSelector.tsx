'use client';

import { useState, useCallback, useMemo } from 'react';
import type { PaceTarget, PaceUnit, TrainingZone, HRTarget } from '@/lib/types';
import { TRAINING_ZONES } from '@/lib/types';

interface PaceSelectorProps {
  value?: PaceTarget;
  hrValue?: HRTarget;
  onChange: (pace: PaceTarget | undefined) => void;
  onHRChange?: (hr: HRTarget | undefined) => void;
  mode?: 'pace' | 'hr' | 'both';
  className?: string;
}

// Convert seconds to MM:SS format
function formatPace(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Parse MM:SS to seconds
function parsePace(value: string): number | null {
  const match = value.match(/^(\d{1,2}):(\d{2})$/);
  if (!match) return null;
  const mins = parseInt(match[1], 10);
  const secs = parseInt(match[2], 10);
  if (secs >= 60) return null;
  return mins * 60 + secs;
}

// Convert pace between km and mile
function convertPace(seconds: number, from: PaceUnit, to: PaceUnit): number {
  if (from === to) return seconds;
  const kmToMile = 1.60934;
  if (from === 'min/km' && to === 'min/mile') {
    return Math.round(seconds * kmToMile);
  }
  return Math.round(seconds / kmToMile);
}

// Default pace ranges for training zones (in seconds per km)
const ZONE_PACE_DEFAULTS: Record<TrainingZone, { min: number; max: number }> = {
  easy: { min: 330, max: 390 }, // 5:30 - 6:30
  tempo: { min: 270, max: 300 }, // 4:30 - 5:00
  threshold: { min: 240, max: 270 }, // 4:00 - 4:30
  interval: { min: 210, max: 240 }, // 3:30 - 4:00
  repetition: { min: 180, max: 210 }, // 3:00 - 3:30
};

export function PaceSelector({
  value,
  hrValue,
  onChange,
  onHRChange,
  mode = 'both',
  className = '',
}: PaceSelectorProps) {
  const [unit, setUnit] = useState<PaceUnit>(value?.unit || 'min/km');
  const [activeMode, setActiveMode] = useState<'pace' | 'hr'>(
    mode === 'hr' ? 'hr' : 'pace'
  );
  const [selectedZone, setSelectedZone] = useState<TrainingZone | null>(null);

  // Local state for pace input
  const [minPaceInput, setMinPaceInput] = useState(
    value ? formatPace(value.min) : ''
  );
  const [maxPaceInput, setMaxPaceInput] = useState(
    value ? formatPace(value.max) : ''
  );

  // Local state for HR input
  const [minHR, setMinHR] = useState(hrValue?.min?.toString() || '');
  const [maxHR, setMaxHR] = useState(hrValue?.max?.toString() || '');

  const handleUnitChange = useCallback(
    (newUnit: PaceUnit) => {
      if (newUnit !== unit && value) {
        const newMin = convertPace(value.min, unit, newUnit);
        const newMax = convertPace(value.max, unit, newUnit);
        setMinPaceInput(formatPace(newMin));
        setMaxPaceInput(formatPace(newMax));
        onChange({
          min: newMin,
          max: newMax,
          unit: newUnit,
        });
      }
      setUnit(newUnit);
    },
    [unit, value, onChange]
  );

  const handlePaceChange = useCallback(
    (type: 'min' | 'max', inputValue: string) => {
      if (type === 'min') {
        setMinPaceInput(inputValue);
      } else {
        setMaxPaceInput(inputValue);
      }

      const minSeconds = parsePace(type === 'min' ? inputValue : minPaceInput);
      const maxSeconds = parsePace(type === 'max' ? inputValue : maxPaceInput);

      if (minSeconds !== null && maxSeconds !== null) {
        onChange({
          min: minSeconds,
          max: maxSeconds,
          unit,
        });
        setSelectedZone(null);
      } else if (inputValue === '') {
        if (
          (type === 'min' && maxPaceInput === '') ||
          (type === 'max' && minPaceInput === '')
        ) {
          onChange(undefined);
        }
      }
    },
    [minPaceInput, maxPaceInput, unit, onChange]
  );

  const handleHRChange = useCallback(
    (type: 'min' | 'max', inputValue: string) => {
      if (type === 'min') {
        setMinHR(inputValue);
      } else {
        setMaxHR(inputValue);
      }

      const min = parseInt(type === 'min' ? inputValue : minHR, 10);
      const max = parseInt(type === 'max' ? inputValue : maxHR, 10);

      if (!isNaN(min) && !isNaN(max) && onHRChange) {
        onHRChange({ min, max });
      } else if (inputValue === '' && onHRChange) {
        if (
          (type === 'min' && maxHR === '') ||
          (type === 'max' && minHR === '')
        ) {
          onHRChange(undefined);
        }
      }
    },
    [minHR, maxHR, onHRChange]
  );

  const handleZoneSelect = useCallback(
    (zone: TrainingZone) => {
      setSelectedZone(zone);
      const defaults = ZONE_PACE_DEFAULTS[zone];
      const paceMin =
        unit === 'min/km'
          ? defaults.min
          : convertPace(defaults.min, 'min/km', 'min/mile');
      const paceMax =
        unit === 'min/km'
          ? defaults.max
          : convertPace(defaults.max, 'min/km', 'min/mile');

      setMinPaceInput(formatPace(paceMin));
      setMaxPaceInput(formatPace(paceMax));
      onChange({
        min: paceMin,
        max: paceMax,
        unit,
      });

      // Also set HR if handler provided
      if (onHRChange) {
        const zoneConfig = TRAINING_ZONES.find((z) => z.zone === zone);
        if (zoneConfig) {
          const maxHREstimate = 185; // Could be made configurable
          const hrMin = Math.round(
            (zoneConfig.hrPercentage.min / 100) * maxHREstimate
          );
          const hrMax = Math.round(
            (zoneConfig.hrPercentage.max / 100) * maxHREstimate
          );
          setMinHR(hrMin.toString());
          setMaxHR(hrMax.toString());
          onHRChange({ min: hrMin, max: hrMax });
        }
      }
    },
    [unit, onChange, onHRChange]
  );

  const zoneButtons = useMemo(
    () =>
      TRAINING_ZONES.map((zone) => (
        <button
          key={zone.zone}
          type="button"
          onClick={() => handleZoneSelect(zone.zone)}
          className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
            selectedZone === zone.zone
              ? 'border-transparent text-white'
              : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
          }`}
          style={{
            backgroundColor:
              selectedZone === zone.zone ? zone.color : 'transparent',
          }}
          title={zone.description}
        >
          {zone.label}
        </button>
      )),
    [selectedZone, handleZoneSelect]
  );

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Mode toggle (if both modes are available) */}
      {mode === 'both' && (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setActiveMode('pace')}
            className={`flex-1 py-2 px-4 text-sm font-medium rounded-lg transition-colors ${
              activeMode === 'pace'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
            }`}
          >
            Pace Target
          </button>
          <button
            type="button"
            onClick={() => setActiveMode('hr')}
            className={`flex-1 py-2 px-4 text-sm font-medium rounded-lg transition-colors ${
              activeMode === 'hr'
                ? 'bg-red-600 text-white'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
            }`}
          >
            HR Target
          </button>
        </div>
      )}

      {/* Training zone presets */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Training Zone Presets
        </label>
        <div className="flex flex-wrap gap-2">{zoneButtons}</div>
      </div>

      {/* Pace inputs */}
      {(mode === 'pace' || (mode === 'both' && activeMode === 'pace')) && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Pace Range
            </label>
            <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5">
              <button
                type="button"
                onClick={() => handleUnitChange('min/km')}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  unit === 'min/km'
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-600 dark:text-gray-400'
                }`}
              >
                min/km
              </button>
              <button
                type="button"
                onClick={() => handleUnitChange('min/mile')}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  unit === 'min/mile'
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-600 dark:text-gray-400'
                }`}
              >
                min/mile
              </button>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex-1">
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                Min (faster)
              </label>
              <input
                type="text"
                value={minPaceInput}
                onChange={(e) => handlePaceChange('min', e.target.value)}
                placeholder="4:00"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <span className="text-gray-400 dark:text-gray-500 pt-5">-</span>
            <div className="flex-1">
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                Max (slower)
              </label>
              <input
                type="text"
                value={maxPaceInput}
                onChange={(e) => handlePaceChange('max', e.target.value)}
                placeholder="5:00"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>
      )}

      {/* HR inputs */}
      {(mode === 'hr' || (mode === 'both' && activeMode === 'hr')) && (
        <div className="space-y-3">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Heart Rate Range (bpm)
          </label>
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                Min
              </label>
              <input
                type="number"
                value={minHR}
                onChange={(e) => handleHRChange('min', e.target.value)}
                placeholder="140"
                min="60"
                max="220"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent"
              />
            </div>
            <span className="text-gray-400 dark:text-gray-500 pt-5">-</span>
            <div className="flex-1">
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                Max
              </label>
              <input
                type="number"
                value={maxHR}
                onChange={(e) => handleHRChange('max', e.target.value)}
                placeholder="160"
                min="60"
                max="220"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>
      )}

      {/* Clear button */}
      {(value || hrValue) && (
        <button
          type="button"
          onClick={() => {
            onChange(undefined);
            onHRChange?.(undefined);
            setMinPaceInput('');
            setMaxPaceInput('');
            setMinHR('');
            setMaxHR('');
            setSelectedZone(null);
          }}
          className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
        >
          Clear targets
        </button>
      )}
    </div>
  );
}

export default PaceSelector;
