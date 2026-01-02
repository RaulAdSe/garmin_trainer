'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { clsx } from 'clsx';
import { useOnboarding, OnboardingStep } from '@/contexts/onboarding-context';
import { WelcomeStep } from './WelcomeStep';
import { ConnectionStep } from './ConnectionStep';
import { ProfileStep } from './ProfileStep';

interface OnboardingFlowProps {
  onComplete?: () => void;
  className?: string;
}

const STEP_CONFIG: { id: OnboardingStep; label: string }[] = [
  { id: 'welcome', label: 'Welcome' },
  { id: 'connection', label: 'Connect' },
  { id: 'profile', label: 'Profile' },
];

export function OnboardingFlow({ onComplete, className }: OnboardingFlowProps) {
  const t = useTranslations('onboarding');
  const { state, isLoading, shouldShowOnboarding, progress } = useOnboarding();
  const [direction, setDirection] = useState<'forward' | 'backward'>('forward');
  const [prevStep, setPrevStep] = useState<OnboardingStep>(state.currentStep);

  // Track step changes for animation direction
  useEffect(() => {
    const currentIndex = STEP_CONFIG.findIndex((s) => s.id === state.currentStep);
    const prevIndex = STEP_CONFIG.findIndex((s) => s.id === prevStep);
    setDirection(currentIndex >= prevIndex ? 'forward' : 'backward');
    setPrevStep(state.currentStep);
  }, [state.currentStep, prevStep]);

  // Callback when onboarding completes
  useEffect(() => {
    if (state.isComplete && onComplete) {
      onComplete();
    }
  }, [state.isComplete, onComplete]);

  if (isLoading) {
    return <OnboardingLoadingSkeleton />;
  }

  if (!shouldShowOnboarding) {
    return null;
  }

  return (
    <div
      className={clsx(
        'fixed inset-0 z-50 bg-gray-950 overflow-y-auto',
        className
      )}
    >
      {/* Progress indicator */}
      <div className="sticky top-0 z-10 bg-gray-950/95 backdrop-blur-sm border-b border-gray-800">
        <div className="max-w-2xl mx-auto px-4 py-4">
          {/* Step indicators */}
          <div className="flex items-center justify-center gap-2 mb-3">
            {STEP_CONFIG.map((step, index) => {
              const currentIndex = STEP_CONFIG.findIndex(
                (s) => s.id === state.currentStep
              );
              const isActive = step.id === state.currentStep;
              const isCompleted = index < currentIndex;

              return (
                <div key={step.id} className="flex items-center">
                  {/* Step dot */}
                  <div
                    className={clsx(
                      'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all',
                      isCompleted && 'bg-teal-500 text-white',
                      isActive && 'bg-teal-500/20 border-2 border-teal-500 text-teal-400',
                      !isActive && !isCompleted && 'bg-gray-800 text-gray-500'
                    )}
                  >
                    {isCompleted ? (
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2.5}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    ) : (
                      index + 1
                    )}
                  </div>

                  {/* Connector line */}
                  {index < STEP_CONFIG.length - 1 && (
                    <div
                      className={clsx(
                        'w-8 sm:w-12 h-0.5 mx-1 transition-colors',
                        isCompleted ? 'bg-teal-500' : 'bg-gray-700'
                      )}
                    />
                  )}
                </div>
              );
            })}
          </div>

          {/* Progress bar */}
          <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-teal-500 to-teal-400 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* Step label */}
          <div className="text-center mt-2">
            <span className="text-xs text-gray-500">
              {t('progress.step', {
                current: STEP_CONFIG.findIndex((s) => s.id === state.currentStep) + 1,
                total: STEP_CONFIG.length,
              })}
            </span>
          </div>
        </div>
      </div>

      {/* Step content */}
      <div className="max-w-2xl mx-auto">
        <div
          className={clsx(
            'transition-all duration-300',
            direction === 'forward' ? 'animate-slideInRight' : 'animate-slideInLeft'
          )}
          key={state.currentStep}
        >
          {state.currentStep === 'welcome' && <WelcomeStep />}
          {state.currentStep === 'connection' && <ConnectionStep />}
          {state.currentStep === 'profile' && <ProfileStep />}
        </div>
      </div>

      {/* Skip button (only on welcome) */}
      {state.currentStep === 'welcome' && (
        <div className="fixed bottom-8 left-0 right-0 flex justify-center">
          <SkipOnboardingButton />
        </div>
      )}
    </div>
  );
}

function SkipOnboardingButton() {
  const t = useTranslations('onboarding');
  const { completeOnboarding } = useOnboarding();

  return (
    <button
      onClick={completeOnboarding}
      className="text-sm text-gray-500 hover:text-gray-300 transition-colors py-2 px-4"
    >
      {t('skipOnboarding')}
    </button>
  );
}

function OnboardingLoadingSkeleton() {
  return (
    <div className="fixed inset-0 z-50 bg-gray-950 flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-800 animate-pulse" />
        <div className="h-6 w-32 mx-auto bg-gray-800 rounded animate-pulse" />
      </div>
    </div>
  );
}

// Export for use as a wrapper component
export function OnboardingWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  const { shouldShowOnboarding, state } = useOnboarding();

  if (shouldShowOnboarding && !state.isComplete) {
    return <OnboardingFlow />;
  }

  return <>{children}</>;
}

// Compact completion celebration component
export function OnboardingComplete() {
  const t = useTranslations('onboarding');
  const { state } = useOnboarding();
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (state.isComplete && state.completedAt) {
      // Check if just completed (within last 5 seconds)
      const completedTime = new Date(state.completedAt).getTime();
      const now = Date.now();
      if (now - completedTime < 5000) {
        setShow(true);
        // Auto-hide after 3 seconds
        const timer = setTimeout(() => setShow(false), 3000);
        return () => clearTimeout(timer);
      }
    }
  }, [state.isComplete, state.completedAt]);

  if (!show) return null;

  return (
    <div className="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 animate-slideUp">
      <div className="bg-teal-500/90 backdrop-blur-sm text-white px-6 py-3 rounded-full shadow-lg shadow-teal-500/20 flex items-center gap-3">
        <span className="text-2xl">🎉</span>
        <span className="font-medium">{t('complete.welcome')}</span>
      </div>
    </div>
  );
}

export default OnboardingFlow;
