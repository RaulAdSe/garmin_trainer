'use client';

import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/Button';
import { useOnboarding } from '@/contexts/onboarding-context';

export function WelcomeStep() {
  const t = useTranslations('onboarding');
  const { nextStep } = useOnboarding();

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4 animate-fadeIn">
      {/* Logo/Icon */}
      <div className="mb-8">
        <div className="relative">
          {/* Animated rings */}
          <div className="absolute inset-0 w-24 h-24 rounded-full bg-teal-500/20 animate-pulse-gentle" />
          <div
            className="absolute inset-2 w-20 h-20 rounded-full bg-teal-500/30 animate-pulse-gentle"
            style={{ animationDelay: '0.3s' }}
          />
          {/* Main icon */}
          <div className="relative w-24 h-24 flex items-center justify-center rounded-full bg-gradient-to-br from-teal-500 to-teal-600 shadow-lg shadow-teal-500/20">
            <svg
              className="w-12 h-12 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"
              />
            </svg>
          </div>
        </div>
      </div>

      {/* App name and tagline */}
      <h1 className="text-3xl sm:text-4xl font-bold text-gray-100 mb-3">
        <span className="gradient-text">trAIner</span>
      </h1>
      <p className="text-lg sm:text-xl text-gray-400 mb-8">
        {t('welcome.tagline')}
      </p>

      {/* Value propositions */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10 max-w-2xl w-full">
        <ValueCard
          icon={<ChartIcon />}
          title={t('welcome.value1Title')}
          description={t('welcome.value1Desc')}
        />
        <ValueCard
          icon={<BrainIcon />}
          title={t('welcome.value2Title')}
          description={t('welcome.value2Desc')}
        />
        <ValueCard
          icon={<TrophyIcon />}
          title={t('welcome.value3Title')}
          description={t('welcome.value3Desc')}
        />
      </div>

      {/* CTA button */}
      <Button
        variant="primary"
        size="lg"
        onClick={nextStep}
        className="min-w-[200px]"
        rightIcon={
          <svg
            className="w-5 h-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 7l5 5m0 0l-5 5m5-5H6"
            />
          </svg>
        }
      >
        {t('welcome.getStarted')}
      </Button>

      {/* Privacy note */}
      <p className="mt-6 text-xs text-gray-500 max-w-md">
        {t('welcome.privacyNote')}
      </p>
    </div>
  );
}

function ValueCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center hover:border-gray-700 transition-colors">
      <div className="w-10 h-10 mx-auto mb-3 flex items-center justify-center rounded-lg bg-teal-500/10 text-teal-400">
        {icon}
      </div>
      <h3 className="text-sm font-semibold text-gray-100 mb-1">{title}</h3>
      <p className="text-xs text-gray-400">{description}</p>
    </div>
  );
}

// Icon components
function ChartIcon() {
  return (
    <svg
      className="w-5 h-5"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
      />
    </svg>
  );
}

function BrainIcon() {
  return (
    <svg
      className="w-5 h-5"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z"
      />
    </svg>
  );
}

function TrophyIcon() {
  return (
    <svg
      className="w-5 h-5"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M16.5 18.75h-9m9 0a3 3 0 013 3h-15a3 3 0 013-3m9 0v-3.375c0-.621-.503-1.125-1.125-1.125h-.871M7.5 18.75v-3.375c0-.621.504-1.125 1.125-1.125h.872m5.007 0H9.497m5.007 0a7.454 7.454 0 01-.982-3.172M9.497 14.25a7.454 7.454 0 00.981-3.172M5.25 4.236c-.982.143-1.954.317-2.916.52A6.003 6.003 0 007.73 9.728M5.25 4.236V4.5c0 2.108.966 3.99 2.48 5.228M5.25 4.236V2.721C7.456 2.41 9.71 2.25 12 2.25c2.291 0 4.545.16 6.75.47v1.516M7.73 9.728a6.726 6.726 0 002.748 1.35m8.272-6.842V4.5c0 2.108-.966 3.99-2.48 5.228m2.48-5.492a46.32 46.32 0 012.916.52 6.003 6.003 0 01-5.395 4.972m0 0a6.726 6.726 0 01-2.749 1.35m0 0a6.772 6.772 0 01-3.044 0"
      />
    </svg>
  );
}

export default WelcomeStep;
