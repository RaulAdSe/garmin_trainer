'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { usePurpose, type PurposeType } from '@/hooks/usePurpose';

interface PurposeOption {
  type: PurposeType;
  icon: React.ReactNode;
  gradient: string;
}

const purposeOptions: PurposeOption[] = [
  {
    type: 'first_5k',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
    gradient: 'from-green-500/20 to-emerald-500/20',
  },
  {
    type: 'first_10k',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
    gradient: 'from-blue-500/20 to-cyan-500/20',
  },
  {
    type: 'first_half',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
      </svg>
    ),
    gradient: 'from-purple-500/20 to-violet-500/20',
  },
  {
    type: 'first_marathon',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
      </svg>
    ),
    gradient: 'from-amber-500/20 to-orange-500/20',
  },
  {
    type: 'beat_pb',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
      </svg>
    ),
    gradient: 'from-red-500/20 to-pink-500/20',
  },
  {
    type: 'stay_healthy',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
      </svg>
    ),
    gradient: 'from-teal-500/20 to-green-500/20',
  },
  {
    type: 'lose_weight',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
      </svg>
    ),
    gradient: 'from-indigo-500/20 to-blue-500/20',
  },
  {
    type: 'enjoy_more',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    gradient: 'from-yellow-500/20 to-amber-500/20',
  },
];

interface PurposeStepProps {
  onComplete?: () => void;
  onSkip?: () => void;
  showSkip?: boolean;
  className?: string;
}

export function PurposeStep({
  onComplete,
  onSkip,
  showSkip = true,
  className,
}: PurposeStepProps) {
  const t = useTranslations('purpose');
  const { updatePurpose, skipOnboarding } = usePurpose();
  const [selectedType, setSelectedType] = useState<PurposeType | null>(null);
  const [customText, setCustomText] = useState('');
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSelectOption = (type: PurposeType) => {
    setSelectedType(type);
    setShowCustomInput(false);
    setCustomText('');
  };

  const handleShowCustom = () => {
    setSelectedType('custom');
    setShowCustomInput(true);
  };

  const handleSubmit = async () => {
    if (!selectedType) return;
    if (selectedType === 'custom' && !customText.trim()) return;

    setIsSubmitting(true);

    try {
      updatePurpose(selectedType, customText.trim() || undefined);
      onComplete?.();
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSkip = () => {
    skipOnboarding();
    onSkip?.();
  };

  const isValid = selectedType !== null && (selectedType !== 'custom' || customText.trim().length > 0);

  return (
    <div className={cn('w-full max-w-2xl mx-auto', className)}>
      {/* Header with motivational copy */}
      <div className="text-center mb-8 animate-fadeIn">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-teal-500/20 to-green-500/20 border border-teal-500/30 mb-4">
          <svg className="w-8 h-8 text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-100 mb-3">
          {t('title')}
        </h2>
        <p className="text-gray-400 text-base sm:text-lg max-w-md mx-auto">
          {t('subtitle')}
        </p>
      </div>

      {/* Purpose options grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
        {purposeOptions.map((option) => (
          <button
            key={option.type}
            onClick={() => handleSelectOption(option.type)}
            className={cn(
              'relative p-4 rounded-xl border text-left transition-all duration-200',
              'hover:scale-[1.02] active:scale-[0.98]',
              selectedType === option.type
                ? 'bg-gradient-to-br border-teal-500/50 shadow-lg shadow-teal-500/10'
                : 'bg-gray-900 border-gray-800 hover:border-gray-700',
              selectedType === option.type && option.gradient
            )}
          >
            {/* Selection indicator */}
            {selectedType === option.type && (
              <div className="absolute top-3 right-3">
                <div className="w-5 h-5 rounded-full bg-teal-500 flex items-center justify-center">
                  <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              </div>
            )}

            <div className="flex items-start gap-3">
              <div
                className={cn(
                  'shrink-0 w-10 h-10 rounded-lg flex items-center justify-center',
                  selectedType === option.type
                    ? 'bg-teal-500/20 text-teal-400'
                    : 'bg-gray-800 text-gray-400'
                )}
              >
                {option.icon}
              </div>
              <div className="flex-1 min-w-0">
                <h3
                  className={cn(
                    'font-semibold text-sm',
                    selectedType === option.type ? 'text-gray-100' : 'text-gray-300'
                  )}
                >
                  {t(`options.${option.type}`)}
                </h3>
                <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                  {t(`descriptions.${option.type}`)}
                </p>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Custom option */}
      <Card
        variant={showCustomInput ? 'elevated' : 'outlined'}
        padding="sm"
        className={cn(
          'transition-all duration-200 cursor-pointer mb-6',
          showCustomInput && 'ring-1 ring-teal-500/50'
        )}
        onClick={() => !showCustomInput && handleShowCustom()}
      >
        <div className="flex items-start gap-3">
          <div
            className={cn(
              'shrink-0 w-10 h-10 rounded-lg flex items-center justify-center',
              showCustomInput
                ? 'bg-teal-500/20 text-teal-400'
                : 'bg-gray-800 text-gray-400'
            )}
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </div>
          <div className="flex-1">
            <h3 className={cn(
              'font-semibold text-sm',
              showCustomInput ? 'text-gray-100' : 'text-gray-300'
            )}>
              {t('customOption')}
            </h3>
            {showCustomInput ? (
              <div className="mt-2" onClick={(e) => e.stopPropagation()}>
                <Input
                  placeholder={t('customPlaceholder')}
                  value={customText}
                  onChange={(e) => setCustomText(e.target.value)}
                  autoFocus
                  size="sm"
                />
              </div>
            ) : (
              <p className="text-xs text-gray-500 mt-0.5">
                {t('customHint')}
              </p>
            )}
          </div>
        </div>
      </Card>

      {/* Action buttons */}
      <div className="flex flex-col sm:flex-row gap-3">
        <Button
          variant="primary"
          size="lg"
          fullWidth
          onClick={handleSubmit}
          disabled={!isValid}
          isLoading={isSubmitting}
          leftIcon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
            </svg>
          }
        >
          {t('setMyPurpose')}
        </Button>

        {showSkip && (
          <Button
            variant="ghost"
            size="lg"
            fullWidth
            onClick={handleSkip}
            className="sm:w-auto sm:px-8"
          >
            {t('skipForNow')}
          </Button>
        )}
      </div>

      {/* Inspirational note */}
      <p className="text-center text-xs text-gray-500 mt-6">
        {t('whyNote')}
      </p>
    </div>
  );
}

export default PurposeStep;
