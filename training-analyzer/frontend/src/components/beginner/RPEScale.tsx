'use client';

import { useState, useCallback, type ReactNode } from 'react';
import { useTranslations } from 'next-intl';
import { clsx } from 'clsx';

export interface RPELevel {
  value: number;
  label: string;
  description: string;
  breathing: string;
  talkTest: string;
  color: string;
  bgColor: string;
  borderColor: string;
}

export interface RPEScaleProps {
  value?: number;
  onChange?: (value: number) => void;
  disabled?: boolean;
  showDetails?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const RPE_LEVELS: RPELevel[] = [
  {
    value: 1,
    label: 'veryLight',
    description: 'barelyMoving',
    breathing: 'normal',
    talkTest: 'fullConversation',
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
    borderColor: 'border-green-500',
  },
  {
    value: 2,
    label: 'veryLight',
    description: 'barelyMoving',
    breathing: 'normal',
    talkTest: 'fullConversation',
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
    borderColor: 'border-green-500',
  },
  {
    value: 3,
    label: 'light',
    description: 'easyEffort',
    breathing: 'slightlyElevated',
    talkTest: 'sentences',
    color: 'text-green-300',
    bgColor: 'bg-green-400/20',
    borderColor: 'border-green-400',
  },
  {
    value: 4,
    label: 'light',
    description: 'easyEffort',
    breathing: 'slightlyElevated',
    talkTest: 'sentences',
    color: 'text-lime-400',
    bgColor: 'bg-lime-500/20',
    borderColor: 'border-lime-500',
  },
  {
    value: 5,
    label: 'moderate',
    description: 'comfortable',
    breathing: 'noticeable',
    talkTest: 'phrases',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/20',
    borderColor: 'border-yellow-500',
  },
  {
    value: 6,
    label: 'moderate',
    description: 'comfortable',
    breathing: 'noticeable',
    talkTest: 'phrases',
    color: 'text-yellow-300',
    bgColor: 'bg-yellow-400/20',
    borderColor: 'border-yellow-400',
  },
  {
    value: 7,
    label: 'hard',
    description: 'challenging',
    breathing: 'heavy',
    talkTest: 'fewWords',
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/20',
    borderColor: 'border-orange-500',
  },
  {
    value: 8,
    label: 'hard',
    description: 'challenging',
    breathing: 'heavy',
    talkTest: 'fewWords',
    color: 'text-orange-300',
    bgColor: 'bg-orange-400/20',
    borderColor: 'border-orange-400',
  },
  {
    value: 9,
    label: 'maximum',
    description: 'allOut',
    breathing: 'gasping',
    talkTest: 'cantTalk',
    color: 'text-red-400',
    bgColor: 'bg-red-500/20',
    borderColor: 'border-red-500',
  },
  {
    value: 10,
    label: 'maximum',
    description: 'allOut',
    breathing: 'gasping',
    talkTest: 'cantTalk',
    color: 'text-red-300',
    bgColor: 'bg-red-400/20',
    borderColor: 'border-red-400',
  },
];

const sizeStyles = {
  sm: {
    button: 'min-w-[36px] min-h-[36px] text-sm',
    details: 'text-xs',
    container: 'gap-1',
  },
  md: {
    button: 'min-w-[44px] min-h-[44px] text-base',
    details: 'text-sm',
    container: 'gap-1.5',
  },
  lg: {
    button: 'min-w-[52px] min-h-[52px] text-lg',
    details: 'text-base',
    container: 'gap-2',
  },
};

export function RPEScale({
  value,
  onChange,
  disabled = false,
  showDetails = true,
  size = 'md',
  className,
}: RPEScaleProps) {
  const t = useTranslations('rpe');
  const [hoveredValue, setHoveredValue] = useState<number | null>(null);

  const handleSelect = useCallback(
    (rpeValue: number) => {
      if (!disabled && onChange) {
        onChange(rpeValue);
      }
    },
    [disabled, onChange]
  );

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent, rpeValue: number) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        handleSelect(rpeValue);
      }
    },
    [handleSelect]
  );

  const activeLevel = hoveredValue
    ? RPE_LEVELS.find((l) => l.value === hoveredValue)
    : value
    ? RPE_LEVELS.find((l) => l.value === value)
    : null;

  const styles = sizeStyles[size];

  return (
    <div className={clsx('w-full', className)}>
      {/* Scale header */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-300">
          {t('title')}
        </span>
        {value && (
          <span className={clsx('text-sm font-semibold', RPE_LEVELS[value - 1]?.color)}>
            {value}/10 - {t(`levels.${RPE_LEVELS[value - 1]?.label}`)}
          </span>
        )}
      </div>

      {/* Scale buttons */}
      <div
        className={clsx(
          'flex flex-wrap justify-center',
          styles.container
        )}
        role="radiogroup"
        aria-label={t('title')}
      >
        {RPE_LEVELS.map((level) => {
          const isSelected = value === level.value;
          const isHovered = hoveredValue === level.value;

          return (
            <button
              key={level.value}
              type="button"
              role="radio"
              aria-checked={isSelected}
              aria-label={`${t('rpeValue', { value: level.value })} - ${t(`levels.${level.label}`)}`}
              disabled={disabled}
              onClick={() => handleSelect(level.value)}
              onKeyDown={(e) => handleKeyDown(e, level.value)}
              onMouseEnter={() => setHoveredValue(level.value)}
              onMouseLeave={() => setHoveredValue(null)}
              onFocus={() => setHoveredValue(level.value)}
              onBlur={() => setHoveredValue(null)}
              className={clsx(
                // Base styles
                'flex items-center justify-center rounded-lg font-semibold',
                'transition-all duration-150 touch-manipulation',
                'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-900',
                // Size styles
                styles.button,
                // State styles
                isSelected
                  ? clsx(
                      level.bgColor,
                      `border-2 ${level.borderColor}`,
                      level.color,
                      'ring-2 ring-offset-1 ring-offset-gray-900',
                      level.borderColor.replace('border-', 'ring-')
                    )
                  : isHovered
                  ? clsx(
                      'bg-gray-700 border-2',
                      level.borderColor,
                      level.color
                    )
                  : clsx(
                      'bg-gray-800 border border-gray-700 text-gray-300',
                      'hover:bg-gray-700 hover:border-gray-600'
                    ),
                // Disabled styles
                disabled && 'opacity-50 cursor-not-allowed',
                !disabled && 'cursor-pointer'
              )}
            >
              {level.value}
            </button>
          );
        })}
      </div>

      {/* Details panel */}
      {showDetails && activeLevel && (
        <div
          className={clsx(
            'mt-4 p-4 rounded-lg border',
            activeLevel.bgColor,
            activeLevel.borderColor,
            'transition-all duration-200'
          )}
        >
          <div className={clsx('font-semibold mb-2', activeLevel.color, styles.details)}>
            {t(`levels.${activeLevel.label}`)} ({activeLevel.value}/10)
          </div>

          <div className={clsx('space-y-2', styles.details)}>
            <DetailRow
              label={t('description')}
              value={t(`descriptions.${activeLevel.description}`)}
              color={activeLevel.color}
            />
            <DetailRow
              label={t('breathing')}
              value={t(`breathingLevels.${activeLevel.breathing}`)}
              color={activeLevel.color}
            />
            <DetailRow
              label={t('talkTest')}
              value={t(`talkTestLevels.${activeLevel.talkTest}`)}
              color={activeLevel.color}
            />
          </div>
        </div>
      )}

      {/* Hint when no selection */}
      {showDetails && !activeLevel && !value && (
        <div className="mt-4 p-4 rounded-lg bg-gray-800 border border-gray-700 text-center">
          <p className="text-sm text-gray-400">{t('selectHint')}</p>
        </div>
      )}
    </div>
  );
}

function DetailRow({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="flex items-start gap-2">
      <span className="text-gray-400 shrink-0">{label}:</span>
      <span className={clsx('font-medium', color)}>{value}</span>
    </div>
  );
}

// Compact inline version for forms
export function RPEScaleCompact({
  value,
  onChange,
  disabled = false,
  className,
}: Omit<RPEScaleProps, 'showDetails' | 'size'>) {
  const t = useTranslations('rpe');

  const handleSelect = useCallback(
    (rpeValue: number) => {
      if (!disabled && onChange) {
        onChange(rpeValue);
      }
    },
    [disabled, onChange]
  );

  return (
    <div className={clsx('w-full', className)}>
      <div className="flex items-center gap-1.5">
        {RPE_LEVELS.map((level) => {
          const isSelected = value === level.value;

          return (
            <button
              key={level.value}
              type="button"
              onClick={() => handleSelect(level.value)}
              disabled={disabled}
              className={clsx(
                'flex-1 min-w-[32px] h-8 rounded text-xs font-semibold',
                'transition-all duration-150 touch-manipulation',
                'focus:outline-none focus:ring-2 focus:ring-teal-500',
                isSelected
                  ? clsx(level.bgColor, level.color, 'border', level.borderColor)
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700',
                disabled && 'opacity-50 cursor-not-allowed'
              )}
              title={t(`levels.${level.label}`)}
            >
              {level.value}
            </button>
          );
        })}
      </div>
      {value && (
        <div className="mt-1 text-xs text-gray-400 text-center">
          {t(`levels.${RPE_LEVELS[value - 1]?.label}`)} - {t(`descriptions.${RPE_LEVELS[value - 1]?.description}`)}
        </div>
      )}
    </div>
  );
}

export default RPEScale;
