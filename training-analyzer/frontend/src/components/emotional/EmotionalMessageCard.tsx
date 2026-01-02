'use client';

import { useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/Card';
import {
  type EmotionalContext,
  type MessageTone,
  getToneColor,
  getContextIcon,
  getContextLabel,
} from '@/lib/emotional-messages';

// Icons - using simple SVG icons inline for portability
const IconX = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M18 6 6 18" />
    <path d="m6 6 12 12" />
  </svg>
);

const IconRefresh = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="14"
    height="14"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
    <path d="M21 3v5h-5" />
    <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
    <path d="M8 16H3v5" />
  </svg>
);

const IconHeart = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
  </svg>
);

const IconSparkles = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
    <path d="M5 3v4" />
    <path d="M19 17v4" />
    <path d="M3 5h4" />
    <path d="M17 19h4" />
  </svg>
);

const IconSun = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2" />
    <path d="M12 20v2" />
    <path d="m4.93 4.93 1.41 1.41" />
    <path d="m17.66 17.66 1.41 1.41" />
    <path d="M2 12h2" />
    <path d="M20 12h2" />
    <path d="m6.34 17.66-1.41 1.41" />
    <path d="m19.07 4.93-1.41 1.41" />
  </svg>
);

interface EmotionalMessageCardProps {
  context: EmotionalContext;
  message: string;
  tone: MessageTone;
  actionSuggestion?: string;
  recoveryTips?: string[];
  alternativeActivities?: string[];
  onDismiss?: () => void;
  onRefresh?: () => void;
  className?: string;
  showRefresh?: boolean;
}

export function EmotionalMessageCard({
  context,
  message,
  tone,
  actionSuggestion,
  recoveryTips,
  alternativeActivities,
  onDismiss,
  onRefresh,
  className,
  showRefresh = true,
}: EmotionalMessageCardProps) {
  const t = useTranslations();
  const [isVisible, setIsVisible] = useState(true);
  const [isAnimatingOut, setIsAnimatingOut] = useState(false);

  const toneColors = getToneColor(tone);

  const handleDismiss = useCallback(() => {
    setIsAnimatingOut(true);
    setTimeout(() => {
      setIsVisible(false);
      onDismiss?.();
    }, 200);
  }, [onDismiss]);

  // Get the appropriate icon based on tone
  const ToneIcon = tone === 'empathetic' ? IconHeart : tone === 'encouraging' ? IconSparkles : IconSun;

  if (!isVisible) return null;

  // Try to translate the message key, fallback to raw message
  const translatedMessage = message.startsWith('emotional.')
    ? t(message, { defaultValue: message })
    : message;
  const translatedAction = actionSuggestion?.startsWith('emotional.')
    ? t(actionSuggestion, { defaultValue: actionSuggestion })
    : actionSuggestion;

  return (
    <Card
      padding="md"
      className={cn(
        'relative overflow-hidden transition-all duration-200',
        toneColors.bg,
        toneColors.border,
        'border',
        isAnimatingOut && 'opacity-0 transform translate-y-2',
        // Entrance animation
        'animate-in fade-in slide-in-from-bottom-2 duration-300',
        className
      )}
    >
      {/* Dismiss button */}
      <button
        onClick={handleDismiss}
        className={cn(
          'absolute top-3 right-3 p-1.5 rounded-full',
          'text-gray-400 hover:text-gray-200',
          'hover:bg-white/10 transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-white/20'
        )}
        aria-label={t('common.close')}
      >
        <IconX />
      </button>

      <div className="flex gap-4">
        {/* Icon */}
        <div
          className={cn(
            'shrink-0 w-10 h-10 rounded-full flex items-center justify-center',
            'bg-white/10',
            toneColors.icon
          )}
        >
          <ToneIcon />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 pr-6">
          {/* Context label */}
          <p className={cn('text-xs font-medium mb-1', toneColors.text)}>
            {t(getContextLabel(context))}
          </p>

          {/* Main message */}
          <p className="text-sm text-gray-100 leading-relaxed mb-2">
            {translatedMessage}
          </p>

          {/* Action suggestion */}
          {translatedAction && (
            <p className="text-xs text-gray-400 italic mb-3">
              {translatedAction}
            </p>
          )}

          {/* Recovery tips (if any) */}
          {recoveryTips && recoveryTips.length > 0 && (
            <div className="mb-3">
              <p className="text-xs font-medium text-gray-400 mb-1">
                {t('emotional.recoveryTips')}:
              </p>
              <ul className="text-xs text-gray-500 space-y-0.5">
                {recoveryTips.slice(0, 3).map((tip, index) => (
                  <li key={index} className="flex items-start gap-1">
                    <span className="text-teal-500 mt-0.5">-</span>
                    <span>
                      {tip.startsWith('emotional.') ? t(tip, { defaultValue: tip }) : tip}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Alternative activities (if any) */}
          {alternativeActivities && alternativeActivities.length > 0 && (
            <div className="mb-3">
              <p className="text-xs font-medium text-gray-400 mb-1">
                {t('emotional.alternatives')}:
              </p>
              <div className="flex flex-wrap gap-1.5">
                {alternativeActivities.slice(0, 4).map((activity, index) => (
                  <span
                    key={index}
                    className={cn(
                      'text-xs px-2 py-0.5 rounded-full',
                      'bg-white/5 text-gray-400'
                    )}
                  >
                    {activity.startsWith('emotional.')
                      ? t(activity, { defaultValue: activity })
                      : activity}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Refresh button */}
          {showRefresh && onRefresh && (
            <button
              onClick={onRefresh}
              className={cn(
                'inline-flex items-center gap-1 text-xs',
                'text-gray-500 hover:text-gray-300 transition-colors',
                'focus:outline-none focus:underline'
              )}
            >
              <IconRefresh />
              <span>{t('emotional.anotherMessage')}</span>
            </button>
          )}
        </div>
      </div>
    </Card>
  );
}

export default EmotionalMessageCard;
