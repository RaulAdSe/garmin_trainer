'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { clsx } from 'clsx';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { useOnboarding } from '@/contexts/onboarding-context';

type ConnectionOption = 'garmin' | 'strava' | 'manual' | 'skip';

export function ConnectionStep() {
  const t = useTranslations('onboarding');
  const { setConnectionType, nextStep, previousStep, state } = useOnboarding();
  const [selected, setSelected] = useState<ConnectionOption | undefined>(
    state.connectionType
  );

  const handleSelect = (option: ConnectionOption) => {
    setSelected(option);
  };

  const handleContinue = () => {
    if (selected) {
      setConnectionType(selected);
      nextStep();
    }
  };

  return (
    <div className="flex flex-col items-center py-6 px-4 animate-fadeIn">
      {/* Header */}
      <div className="text-center mb-8">
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-100 mb-2">
          {t('connection.title')}
        </h2>
        <p className="text-gray-400 max-w-md">
          {t('connection.subtitle')}
        </p>
      </div>

      {/* Connection options */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-2xl mb-8">
        <ConnectionCard
          icon={<GarminIcon />}
          title={t('connection.garminTitle')}
          description={t('connection.garminDesc')}
          isSelected={selected === 'garmin'}
          isPrimary
          onClick={() => handleSelect('garmin')}
        />
        <ConnectionCard
          icon={<StravaIcon />}
          title={t('connection.stravaTitle')}
          description={t('connection.stravaDesc')}
          isSelected={selected === 'strava'}
          isPrimary
          onClick={() => handleSelect('strava')}
        />
        <ConnectionCard
          icon={<ManualIcon />}
          title={t('connection.manualTitle')}
          description={t('connection.manualDesc')}
          isSelected={selected === 'manual'}
          onClick={() => handleSelect('manual')}
        />
        <ConnectionCard
          icon={<SkipIcon />}
          title={t('connection.skipTitle')}
          description={t('connection.skipDesc')}
          isSelected={selected === 'skip'}
          onClick={() => handleSelect('skip')}
        />
      </div>

      {/* Feature highlights for connected users */}
      {(selected === 'garmin' || selected === 'strava') && (
        <div className="w-full max-w-2xl mb-8 animate-slideUp">
          <Card variant="outlined" padding="md">
            <h3 className="text-sm font-semibold text-gray-100 mb-3">
              {t('connection.benefitsTitle')}
            </h3>
            <ul className="space-y-2">
              <BenefitItem text={t('connection.benefit1')} />
              <BenefitItem text={t('connection.benefit2')} />
              <BenefitItem text={t('connection.benefit3')} />
              <BenefitItem text={t('connection.benefit4')} />
            </ul>
          </Card>
        </div>
      )}

      {/* Navigation buttons */}
      <div className="flex gap-3 w-full max-w-md">
        <Button
          variant="outline"
          onClick={previousStep}
          leftIcon={
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M11 17l-5-5m0 0l5-5m-5 5h12"
              />
            </svg>
          }
        >
          {t('common.back')}
        </Button>
        <Button
          variant="primary"
          onClick={handleContinue}
          disabled={!selected}
          fullWidth
          rightIcon={
            <svg
              className="w-4 h-4"
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
          {t('common.continue')}
        </Button>
      </div>
    </div>
  );
}

function ConnectionCard({
  icon,
  title,
  description,
  isSelected,
  isPrimary,
  onClick,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  isSelected: boolean;
  isPrimary?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'flex items-start gap-4 p-4 rounded-xl border-2 text-left transition-all',
        'focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 focus:ring-offset-gray-950',
        isSelected
          ? 'border-teal-500 bg-teal-500/10'
          : 'border-gray-700 bg-gray-900 hover:border-gray-600 hover:bg-gray-800/50',
        isPrimary && !isSelected && 'border-dashed'
      )}
    >
      {/* Selection indicator */}
      <div
        className={clsx(
          'shrink-0 w-5 h-5 rounded-full border-2 flex items-center justify-center mt-0.5 transition-colors',
          isSelected
            ? 'border-teal-500 bg-teal-500'
            : 'border-gray-600 bg-transparent'
        )}
      >
        {isSelected && (
          <svg
            className="w-3 h-3 text-white"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={3}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M5 13l4 4L19 7"
            />
          </svg>
        )}
      </div>

      {/* Content */}
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span
            className={clsx(
              'text-lg',
              isSelected ? 'text-teal-400' : 'text-gray-400'
            )}
          >
            {icon}
          </span>
          <h3
            className={clsx(
              'font-semibold',
              isSelected ? 'text-gray-100' : 'text-gray-200'
            )}
          >
            {title}
          </h3>
        </div>
        <p className="text-sm text-gray-400">{description}</p>
      </div>
    </button>
  );
}

function BenefitItem({ text }: { text: string }) {
  return (
    <li className="flex items-center gap-2 text-sm text-gray-300">
      <svg
        className="w-4 h-4 text-teal-400 shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M5 13l4 4L19 7"
        />
      </svg>
      {text}
    </li>
  );
}

// Icon components
function GarminIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z" />
    </svg>
  );
}

function StravaIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
      <path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066l-2.084 4.116zM8.97 6.17L13.333 14h4.305L8.97 0 0 18.667h4.305L8.97 6.17z" />
    </svg>
  );
}

function ManualIcon() {
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
        d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10"
      />
    </svg>
  );
}

function SkipIcon() {
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
        d="M3 8.688c0-.864.933-1.405 1.683-.977l7.108 4.062a1.125 1.125 0 010 1.953l-7.108 4.062A1.125 1.125 0 013 16.81V8.688zM12.75 8.688c0-.864.933-1.405 1.683-.977l7.108 4.062a1.125 1.125 0 010 1.953l-7.108 4.062a1.125 1.125 0 01-1.683-.977V8.688z"
      />
    </svg>
  );
}

export default ConnectionStep;
