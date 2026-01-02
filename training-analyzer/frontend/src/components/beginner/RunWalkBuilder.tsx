'use client';

import { useState, useCallback, useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import type { RunWalkInterval } from '@/lib/types';

interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  formatValue: (value: number) => string;
  onChange: (value: number) => void;
  color?: 'green' | 'blue' | 'purple';
}

function Slider({
  label,
  value,
  min,
  max,
  step = 1,
  formatValue,
  onChange,
  color = 'green',
}: SliderProps) {
  const percentage = ((value - min) / (max - min)) * 100;

  const colorClasses = {
    green: {
      track: 'bg-green-500',
      thumb: 'border-green-500',
      text: 'text-green-400',
    },
    blue: {
      track: 'bg-blue-500',
      thumb: 'border-blue-500',
      text: 'text-blue-400',
    },
    purple: {
      track: 'bg-purple-500',
      thumb: 'border-purple-500',
      text: 'text-purple-400',
    },
  };

  const colors = colorClasses[color];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-300">{label}</span>
        <span className={cn('text-lg font-bold', colors.text)}>
          {formatValue(value)}
        </span>
      </div>
      <div className="relative">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className={cn(
            'w-full h-2 rounded-full appearance-none cursor-pointer',
            'bg-gray-700',
            '[&::-webkit-slider-thumb]:appearance-none',
            '[&::-webkit-slider-thumb]:w-5',
            '[&::-webkit-slider-thumb]:h-5',
            '[&::-webkit-slider-thumb]:rounded-full',
            '[&::-webkit-slider-thumb]:bg-gray-900',
            '[&::-webkit-slider-thumb]:border-2',
            `[&::-webkit-slider-thumb]:${colors.thumb}`,
            '[&::-webkit-slider-thumb]:cursor-pointer',
            '[&::-webkit-slider-thumb]:transition-transform',
            '[&::-webkit-slider-thumb]:hover:scale-110',
            '[&::-moz-range-thumb]:w-5',
            '[&::-moz-range-thumb]:h-5',
            '[&::-moz-range-thumb]:rounded-full',
            '[&::-moz-range-thumb]:bg-gray-900',
            '[&::-moz-range-thumb]:border-2',
            `[&::-moz-range-thumb]:${colors.thumb}`,
            '[&::-moz-range-thumb]:cursor-pointer'
          )}
          style={{
            background: `linear-gradient(to right, ${
              color === 'green'
                ? '#22c55e'
                : color === 'blue'
                  ? '#3b82f6'
                  : '#a855f7'
            } 0%, ${
              color === 'green'
                ? '#22c55e'
                : color === 'blue'
                  ? '#3b82f6'
                  : '#a855f7'
            } ${percentage}%, #374151 ${percentage}%, #374151 100%)`,
          }}
        />
      </div>
    </div>
  );
}

function formatDurationFull(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins === 0) return `${secs} sec`;
  if (secs === 0) return `${mins} min`;
  return `${mins} min ${secs} sec`;
}

function formatDurationShort(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins === 0) return `${secs}s`;
  if (secs === 0) return `${mins}m`;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

interface RunWalkBuilderProps {
  initialValues?: RunWalkInterval;
  onSaveTemplate?: (intervals: RunWalkInterval, name: string) => void;
  onStartWorkout?: (intervals: RunWalkInterval) => void;
  className?: string;
}

export function RunWalkBuilder({
  initialValues,
  onSaveTemplate,
  onStartWorkout,
  className,
}: RunWalkBuilderProps) {
  const t = useTranslations('runWalk');

  const [runSeconds, setRunSeconds] = useState(initialValues?.runSeconds ?? 60);
  const [walkSeconds, setWalkSeconds] = useState(
    initialValues?.walkSeconds ?? 90
  );
  const [repetitions, setRepetitions] = useState(
    initialValues?.repetitions ?? 8
  );
  const [templateName, setTemplateName] = useState('');
  const [showSaveDialog, setShowSaveDialog] = useState(false);

  // Calculate workout structure
  const workoutStructure = useMemo(() => {
    const intervals: { type: 'run' | 'walk'; duration: number }[] = [];
    for (let i = 0; i < repetitions; i++) {
      intervals.push({ type: 'run', duration: runSeconds });
      if (walkSeconds > 0) {
        intervals.push({ type: 'walk', duration: walkSeconds });
      }
    }
    return intervals;
  }, [runSeconds, walkSeconds, repetitions]);

  // Calculate totals
  const totalDuration = (runSeconds + walkSeconds) * repetitions;
  const totalRunTime = runSeconds * repetitions;
  const totalWalkTime = walkSeconds * repetitions;

  const handleStartWorkout = useCallback(() => {
    if (onStartWorkout) {
      onStartWorkout({
        runSeconds,
        walkSeconds,
        repetitions,
      });
    }
  }, [runSeconds, walkSeconds, repetitions, onStartWorkout]);

  const handleSaveTemplate = useCallback(() => {
    if (onSaveTemplate && templateName.trim()) {
      onSaveTemplate(
        {
          runSeconds,
          walkSeconds,
          repetitions,
        },
        templateName.trim()
      );
      setShowSaveDialog(false);
      setTemplateName('');
    }
  }, [runSeconds, walkSeconds, repetitions, templateName, onSaveTemplate]);

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-white">{t('builderTitle')}</h2>
        <p className="mt-1 text-sm text-gray-400">{t('builderSubtitle')}</p>
      </div>

      {/* Sliders */}
      <div className="space-y-6 p-4 bg-gray-800/50 rounded-xl border border-gray-700">
        <Slider
          label={t('runDuration')}
          value={runSeconds}
          min={30}
          max={600}
          step={30}
          formatValue={formatDurationFull}
          onChange={setRunSeconds}
          color="green"
        />

        <Slider
          label={t('walkDuration')}
          value={walkSeconds}
          min={0}
          max={300}
          step={15}
          formatValue={(v) => (v === 0 ? t('noWalk') : formatDurationFull(v))}
          onChange={setWalkSeconds}
          color="blue"
        />

        <Slider
          label={t('repetitionsLabel')}
          value={repetitions}
          min={1}
          max={20}
          step={1}
          formatValue={(v) => `${v}x`}
          onChange={setRepetitions}
          color="purple"
        />
      </div>

      {/* Total time display */}
      <div className="p-4 bg-gradient-to-r from-teal-500/10 to-green-500/10 rounded-xl border border-teal-500/30">
        <div className="text-center">
          <div className="text-3xl font-bold text-white">
            {Math.floor(totalDuration / 60)} {t('minutes')}
          </div>
          <div className="mt-1 text-sm text-gray-400">{t('totalWorkout')}</div>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-4 text-center">
          <div>
            <div className="text-lg font-semibold text-green-400">
              {formatDurationShort(totalRunTime)}
            </div>
            <div className="text-xs text-gray-500">{t('totalRun')}</div>
          </div>
          <div>
            <div className="text-lg font-semibold text-blue-400">
              {formatDurationShort(totalWalkTime)}
            </div>
            <div className="text-xs text-gray-500">{t('totalWalk')}</div>
          </div>
        </div>
      </div>

      {/* Workout preview */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-gray-300">
          {t('workoutPreview')}
        </h3>
        <div className="flex flex-wrap gap-1.5">
          {workoutStructure.map((interval, index) => (
            <div
              key={index}
              className={cn(
                'px-2 py-1 rounded text-xs font-medium',
                interval.type === 'run'
                  ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                  : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
              )}
            >
              {interval.type === 'run' ? t('run') : t('walk')}{' '}
              {formatDurationShort(interval.duration)}
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-500">
          {t('previewNote', {
            intervals: workoutStructure.length,
            reps: repetitions,
          })}
        </p>
      </div>

      {/* Action buttons */}
      <div className="flex flex-col gap-3 sm:flex-row">
        {onStartWorkout && (
          <button
            type="button"
            onClick={handleStartWorkout}
            className={cn(
              'flex-1 py-3 px-6 rounded-xl font-semibold',
              'bg-gradient-to-r from-teal-500 to-green-500 text-white',
              'hover:from-teal-400 hover:to-green-400',
              'focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 focus:ring-offset-gray-900',
              'transition-all duration-200'
            )}
          >
            {t('startCustomWorkout')}
          </button>
        )}

        {onSaveTemplate && (
          <button
            type="button"
            onClick={() => setShowSaveDialog(true)}
            className={cn(
              'py-3 px-6 rounded-xl font-semibold',
              'border-2 border-gray-600 text-gray-300',
              'hover:border-gray-500 hover:bg-gray-800',
              'focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 focus:ring-offset-gray-900',
              'transition-all duration-200'
            )}
          >
            {t('saveAsTemplate')}
          </button>
        )}
      </div>

      {/* Save template dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md p-6 bg-gray-800 rounded-2xl border border-gray-700 shadow-xl">
            <h3 className="text-lg font-semibold text-white">
              {t('saveTemplateTitle')}
            </h3>
            <p className="mt-1 text-sm text-gray-400">
              {t('saveTemplateSubtitle')}
            </p>

            <div className="mt-4">
              <label
                htmlFor="template-name"
                className="block text-sm font-medium text-gray-300 mb-2"
              >
                {t('templateNameLabel')}
              </label>
              <input
                id="template-name"
                type="text"
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
                placeholder={t('templateNamePlaceholder')}
                className={cn(
                  'w-full px-4 py-3 rounded-xl',
                  'bg-gray-700 border border-gray-600 text-white placeholder-gray-500',
                  'focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent'
                )}
                autoFocus
              />
            </div>

            <div className="mt-2 p-3 bg-gray-700/50 rounded-lg text-sm text-gray-400">
              {formatDurationFull(runSeconds)} {t('run')} /{' '}
              {walkSeconds > 0
                ? `${formatDurationFull(walkSeconds)} ${t('walk')}`
                : t('noWalk')}{' '}
              x {repetitions}
            </div>

            <div className="mt-6 flex gap-3">
              <button
                type="button"
                onClick={() => {
                  setShowSaveDialog(false);
                  setTemplateName('');
                }}
                className={cn(
                  'flex-1 py-2.5 px-4 rounded-lg font-medium',
                  'border border-gray-600 text-gray-300',
                  'hover:bg-gray-700',
                  'focus:outline-none focus:ring-2 focus:ring-gray-500'
                )}
              >
                {t('cancel')}
              </button>
              <button
                type="button"
                onClick={handleSaveTemplate}
                disabled={!templateName.trim()}
                className={cn(
                  'flex-1 py-2.5 px-4 rounded-lg font-medium',
                  'bg-teal-500 text-white',
                  'hover:bg-teal-400',
                  'focus:outline-none focus:ring-2 focus:ring-teal-500',
                  'disabled:opacity-50 disabled:cursor-not-allowed'
                )}
              >
                {t('saveTemplate')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default RunWalkBuilder;
