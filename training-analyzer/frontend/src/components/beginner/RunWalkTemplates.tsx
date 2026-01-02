'use client';

import { useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import type { RunWalkTemplate, RunWalkInterval } from '@/lib/types';

// Couch-to-5K style progressive templates
export const RUN_WALK_TEMPLATES: RunWalkTemplate[] = [
  {
    id: 'week-1',
    name: 'Week 1',
    runSec: 60,
    walkSec: 90,
    reps: 8,
    description: '1 min run, 1.5 min walk',
    weekNumber: 1,
  },
  {
    id: 'week-2',
    name: 'Week 2',
    runSec: 90,
    walkSec: 90,
    reps: 7,
    description: '1.5 min run, 1.5 min walk',
    weekNumber: 2,
  },
  {
    id: 'week-3',
    name: 'Week 3',
    runSec: 120,
    walkSec: 120,
    reps: 6,
    description: '2 min run, 2 min walk',
    weekNumber: 3,
  },
  {
    id: 'week-4',
    name: 'Week 4',
    runSec: 180,
    walkSec: 90,
    reps: 5,
    description: '3 min run, 1.5 min walk',
    weekNumber: 4,
  },
  {
    id: 'week-5',
    name: 'Week 5',
    runSec: 300,
    walkSec: 60,
    reps: 4,
    description: '5 min run, 1 min walk',
    weekNumber: 5,
  },
  {
    id: 'week-6',
    name: 'Week 6',
    runSec: 480,
    walkSec: 60,
    reps: 3,
    description: '8 min run, 1 min walk',
    weekNumber: 6,
  },
  {
    id: 'week-7',
    name: 'Week 7',
    runSec: 600,
    walkSec: 60,
    reps: 2,
    description: '10 min run, 1 min walk',
    weekNumber: 7,
  },
  {
    id: 'week-8',
    name: 'Week 8',
    runSec: 900,
    walkSec: 0,
    reps: 2,
    description: '15 min continuous',
    weekNumber: 8,
  },
];

function formatDuration(seconds: number): string {
  if (seconds === 0) return '0';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins === 0) return `${secs}s`;
  if (secs === 0) return `${mins}m`;
  return `${mins}m ${secs}s`;
}

function calculateTotalDuration(template: RunWalkTemplate): number {
  return (template.runSec + template.walkSec) * template.reps;
}

interface TemplateCardProps {
  template: RunWalkTemplate;
  isSelected?: boolean;
  onSelect: (template: RunWalkTemplate) => void;
}

function TemplateCard({ template, isSelected, onSelect }: TemplateCardProps) {
  const t = useTranslations('runWalk');
  const totalDuration = calculateTotalDuration(template);
  const totalMins = Math.round(totalDuration / 60);

  return (
    <button
      type="button"
      onClick={() => onSelect(template)}
      className={cn(
        'w-full text-left p-4 rounded-xl border-2 transition-all duration-200',
        'focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 focus:ring-offset-gray-900',
        isSelected
          ? 'border-teal-500 bg-teal-500/10'
          : 'border-gray-700 bg-gray-800/50 hover:border-gray-600 hover:bg-gray-800'
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            {template.weekNumber && (
              <span
                className={cn(
                  'inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold',
                  isSelected
                    ? 'bg-teal-500 text-white'
                    : 'bg-gray-700 text-gray-300'
                )}
              >
                {template.weekNumber}
              </span>
            )}
            <h3
              className={cn(
                'font-semibold',
                isSelected ? 'text-teal-400' : 'text-white'
              )}
            >
              {t(`templates.${template.id}.name`, { fallback: template.name })}
            </h3>
          </div>

          <p className="mt-1 text-sm text-gray-400">
            {t(`templates.${template.id}.description`, {
              fallback: template.description,
            })}
          </p>

          <div className="mt-3 flex flex-wrap gap-3 text-xs">
            <div className="flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-full bg-green-500" />
              <span className="text-gray-400">
                {t('run')}: {formatDuration(template.runSec)}
              </span>
            </div>
            {template.walkSec > 0 && (
              <div className="flex items-center gap-1.5">
                <span className="inline-block w-2 h-2 rounded-full bg-blue-500" />
                <span className="text-gray-400">
                  {t('walk')}: {formatDuration(template.walkSec)}
                </span>
              </div>
            )}
            <div className="flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-full bg-purple-500" />
              <span className="text-gray-400">
                {template.reps}x {t('repetitions')}
              </span>
            </div>
          </div>
        </div>

        <div className="text-right shrink-0">
          <div
            className={cn(
              'text-2xl font-bold',
              isSelected ? 'text-teal-400' : 'text-white'
            )}
          >
            {totalMins}
          </div>
          <div className="text-xs text-gray-500">{t('minutes')}</div>
        </div>
      </div>

      {/* Progress indicator for continuous running */}
      {template.walkSec === 0 && (
        <div className="mt-3 px-2 py-1.5 bg-amber-500/10 border border-amber-500/30 rounded-lg">
          <p className="text-xs text-amber-400 font-medium">
            {t('continuousRun')}
          </p>
        </div>
      )}
    </button>
  );
}

interface RunWalkTemplatesProps {
  selectedTemplate?: RunWalkTemplate | null;
  onSelectTemplate: (template: RunWalkTemplate) => void;
  onStartWorkout?: (intervals: RunWalkInterval) => void;
  className?: string;
}

export function RunWalkTemplates({
  selectedTemplate,
  onSelectTemplate,
  onStartWorkout,
  className,
}: RunWalkTemplatesProps) {
  const t = useTranslations('runWalk');

  const handleSelect = useCallback(
    (template: RunWalkTemplate) => {
      onSelectTemplate(template);
    },
    [onSelectTemplate]
  );

  const handleStartWorkout = useCallback(() => {
    if (selectedTemplate && onStartWorkout) {
      onStartWorkout({
        runSeconds: selectedTemplate.runSec,
        walkSeconds: selectedTemplate.walkSec,
        repetitions: selectedTemplate.reps,
      });
    }
  }, [selectedTemplate, onStartWorkout]);

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-white">{t('templatesTitle')}</h2>
        <p className="mt-1 text-sm text-gray-400">{t('templatesSubtitle')}</p>
      </div>

      {/* Template grid */}
      <div className="grid gap-3 sm:grid-cols-2">
        {RUN_WALK_TEMPLATES.map((template) => (
          <TemplateCard
            key={template.id}
            template={template}
            isSelected={selectedTemplate?.id === template.id}
            onSelect={handleSelect}
          />
        ))}
      </div>

      {/* Start button */}
      {selectedTemplate && onStartWorkout && (
        <div className="sticky bottom-0 pt-4 pb-2 bg-gradient-to-t from-gray-900 via-gray-900 to-transparent -mx-4 px-4">
          <button
            type="button"
            onClick={handleStartWorkout}
            className={cn(
              'w-full py-4 px-6 rounded-xl font-semibold text-lg',
              'bg-gradient-to-r from-teal-500 to-green-500 text-white',
              'hover:from-teal-400 hover:to-green-400',
              'focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 focus:ring-offset-gray-900',
              'transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98]'
            )}
          >
            {t('startWorkout', { name: selectedTemplate.name })}
          </button>
        </div>
      )}
    </div>
  );
}

export default RunWalkTemplates;
