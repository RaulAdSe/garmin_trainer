'use client';

import { useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { usePurpose } from '@/hooks/usePurpose';

interface PurposeReminderProps {
  lastWorkoutDate?: string;
  currentStreak?: number;
  onDismiss?: () => void;
  className?: string;
}

// Motivational messages based on context
type ReminderContext = 'streak_broken' | 'inactive' | 'check_in' | 'encouragement';

const contextIcons: Record<ReminderContext, React.ReactNode> = {
  streak_broken: (
    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" />
    </svg>
  ),
  inactive: (
    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
    </svg>
  ),
  check_in: (
    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
    </svg>
  ),
  encouragement: (
    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
    </svg>
  ),
};

const contextGradients: Record<ReminderContext, string> = {
  streak_broken: 'from-orange-500/20 to-amber-500/20',
  inactive: 'from-red-500/20 to-pink-500/20',
  check_in: 'from-teal-500/20 to-cyan-500/20',
  encouragement: 'from-purple-500/20 to-violet-500/20',
};

const contextBorders: Record<ReminderContext, string> = {
  streak_broken: 'border-orange-500/30',
  inactive: 'border-red-500/30',
  check_in: 'border-teal-500/30',
  encouragement: 'border-purple-500/30',
};

const contextIconColors: Record<ReminderContext, string> = {
  streak_broken: 'text-orange-400',
  inactive: 'text-red-400',
  check_in: 'text-teal-400',
  encouragement: 'text-purple-400',
};

export function PurposeReminder({
  lastWorkoutDate,
  currentStreak = 0,
  onDismiss,
  className,
}: PurposeReminderProps) {
  const t = useTranslations('purpose');
  const {
    purpose,
    isLoading,
    shouldShowReminder,
    dismissReminder,
    getPurposeDisplayText,
  } = usePurpose();

  const [isVisible, setIsVisible] = useState(true);
  const [isAnimatingOut, setIsAnimatingOut] = useState(false);

  // Determine the context for the reminder
  const getContext = useCallback((): ReminderContext => {
    if (!lastWorkoutDate) return 'check_in';

    const lastWorkout = new Date(lastWorkoutDate);
    const now = new Date();
    const daysSinceWorkout = Math.floor(
      (now.getTime() - lastWorkout.getTime()) / (1000 * 60 * 60 * 24)
    );

    if (currentStreak === 0 && daysSinceWorkout >= 3) {
      return daysSinceWorkout >= 7 ? 'inactive' : 'streak_broken';
    }

    return 'check_in';
  }, [lastWorkoutDate, currentStreak]);

  const handleDismiss = useCallback(() => {
    setIsAnimatingOut(true);
    setTimeout(() => {
      setIsVisible(false);
      dismissReminder();
      onDismiss?.();
    }, 300);
  }, [dismissReminder, onDismiss]);

  // Don't render if loading or shouldn't show
  if (isLoading) return null;
  if (!purpose) return null;
  if (!shouldShowReminder(lastWorkoutDate, currentStreak)) return null;
  if (!isVisible) return null;

  const context = getContext();
  const purposeText = getPurposeDisplayText(t);

  return (
    <Card
      variant="elevated"
      padding="md"
      className={cn(
        'relative overflow-hidden transition-all duration-300',
        isAnimatingOut && 'opacity-0 scale-95',
        className
      )}
    >
      {/* Gradient background */}
      <div
        className={cn(
          'absolute inset-0 bg-gradient-to-br opacity-50',
          contextGradients[context]
        )}
      />

      {/* Content */}
      <div className="relative">
        {/* Dismiss button */}
        <button
          onClick={handleDismiss}
          className="absolute top-0 right-0 p-1 text-gray-500 hover:text-gray-300 transition-colors"
          aria-label={t('dismiss')}
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {/* Header with icon */}
        <div className="flex items-start gap-4 mb-4">
          <div
            className={cn(
              'shrink-0 w-12 h-12 rounded-xl flex items-center justify-center',
              'bg-gradient-to-br',
              contextGradients[context],
              'border',
              contextBorders[context]
            )}
          >
            <span className={contextIconColors[context]}>
              {contextIcons[context]}
            </span>
          </div>

          <div className="flex-1 min-w-0 pr-6">
            <h3 className="font-semibold text-gray-100 text-sm sm:text-base">
              {t(`reminder.${context}.title`)}
            </h3>
            <p className="text-gray-400 text-sm mt-1">
              {t(`reminder.${context}.message`)}
            </p>
          </div>
        </div>

        {/* Purpose display */}
        <div
          className={cn(
            'rounded-lg p-4 mb-4',
            'bg-gray-900/60 border',
            contextBorders[context]
          )}
        >
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">
            {t('yourWhy')}
          </p>
          <p className="text-gray-100 font-medium text-base sm:text-lg">
            "{purposeText}"
          </p>
        </div>

        {/* Motivational quote */}
        <p className="text-gray-500 text-sm italic mb-4">
          {t(`reminder.${context}.quote`)}
        </p>

        {/* Action buttons */}
        <div className="flex flex-col sm:flex-row gap-2">
          <Button
            variant="primary"
            size="sm"
            className="flex-1"
            onClick={handleDismiss}
            leftIcon={
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            }
          >
            {t('reminder.letsGo')}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDismiss}
            className="sm:w-auto"
          >
            {t('reminder.remindLater')}
          </Button>
        </div>
      </div>
    </Card>
  );
}

// Compact version for tighter spaces
export function PurposeReminderCompact({
  lastWorkoutDate,
  currentStreak = 0,
  onDismiss,
  className,
}: PurposeReminderProps) {
  const t = useTranslations('purpose');
  const {
    purpose,
    isLoading,
    shouldShowReminder,
    dismissReminder,
    getPurposeDisplayText,
  } = usePurpose();

  const [isVisible, setIsVisible] = useState(true);

  const handleDismiss = useCallback(() => {
    setIsVisible(false);
    dismissReminder();
    onDismiss?.();
  }, [dismissReminder, onDismiss]);

  if (isLoading) return null;
  if (!purpose) return null;
  if (!shouldShowReminder(lastWorkoutDate, currentStreak)) return null;
  if (!isVisible) return null;

  const purposeText = getPurposeDisplayText(t);

  return (
    <div
      className={cn(
        'flex items-center gap-3 p-3 rounded-lg',
        'bg-gradient-to-r from-teal-500/10 to-cyan-500/10',
        'border border-teal-500/20',
        className
      )}
    >
      <div className="shrink-0 w-8 h-8 rounded-full bg-teal-500/20 flex items-center justify-center">
        <svg className="w-4 h-4 text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-400">{t('remember')}</p>
        <p className="text-sm text-gray-200 font-medium truncate">
          {purposeText}
        </p>
      </div>

      <button
        onClick={handleDismiss}
        className="shrink-0 p-1 text-gray-500 hover:text-gray-300 transition-colors"
        aria-label={t('dismiss')}
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}

export default PurposeReminder;
