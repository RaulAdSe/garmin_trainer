'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { clsx } from 'clsx';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { useOnboarding, OnboardingProfile } from '@/contexts/onboarding-context';

type ProfileSection = 'goals' | 'zones' | 'preferences';

export function ProfileStep() {
  const t = useTranslations('onboarding');
  const { state, updateProfile, previousStep, completeOnboarding } = useOnboarding();
  const [activeSection, setActiveSection] = useState<ProfileSection>('goals');
  const [localProfile, setLocalProfile] = useState<OnboardingProfile>(state.profile);

  const updateLocalProfile = (updates: Partial<OnboardingProfile>) => {
    setLocalProfile((prev) => ({ ...prev, ...updates }));
  };

  const handleComplete = () => {
    updateProfile(localProfile);
    completeOnboarding();
  };

  const sections: { id: ProfileSection; label: string; isComplete: boolean }[] = [
    {
      id: 'goals',
      label: t('profile.goalsTab'),
      isComplete: !!localProfile.primaryGoal,
    },
    {
      id: 'zones',
      label: t('profile.zonesTab'),
      isComplete: !!localProfile.zoneMethod,
    },
    {
      id: 'preferences',
      label: t('profile.preferencesTab'),
      isComplete: !!localProfile.units,
    },
  ];

  return (
    <div className="flex flex-col items-center py-6 px-4 animate-fadeIn">
      {/* Header */}
      <div className="text-center mb-6">
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-100 mb-2">
          {t('profile.title')}
        </h2>
        <p className="text-gray-400 max-w-md">{t('profile.subtitle')}</p>
      </div>

      {/* Section tabs */}
      <div className="flex gap-2 mb-6 w-full max-w-lg overflow-x-auto pb-2 hide-scrollbar">
        {sections.map((section) => (
          <button
            key={section.id}
            onClick={() => setActiveSection(section.id)}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap',
              'focus:outline-none focus:ring-2 focus:ring-teal-500',
              activeSection === section.id
                ? 'bg-teal-500/20 text-teal-400 border border-teal-500/50'
                : 'bg-gray-800 text-gray-400 hover:text-gray-200 hover:bg-gray-700 border border-transparent'
            )}
          >
            {section.isComplete && (
              <svg
                className="w-4 h-4 text-green-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            )}
            {section.label}
          </button>
        ))}
      </div>

      {/* Section content */}
      <div className="w-full max-w-lg mb-8">
        {activeSection === 'goals' && (
          <GoalsSection profile={localProfile} onUpdate={updateLocalProfile} />
        )}
        {activeSection === 'zones' && (
          <ZonesSection profile={localProfile} onUpdate={updateLocalProfile} />
        )}
        {activeSection === 'preferences' && (
          <PreferencesSection profile={localProfile} onUpdate={updateLocalProfile} />
        )}
      </div>

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
          onClick={handleComplete}
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
                d="M5 13l4 4L19 7"
              />
            </svg>
          }
        >
          {t('profile.finish')}
        </Button>
      </div>
    </div>
  );
}

// Goals Section
function GoalsSection({
  profile,
  onUpdate,
}: {
  profile: OnboardingProfile;
  onUpdate: (updates: Partial<OnboardingProfile>) => void;
}) {
  const t = useTranslations('onboarding');

  const goals = [
    { id: 'race', label: t('profile.goalRace'), icon: TrophyIcon },
    { id: 'fitness', label: t('profile.goalFitness'), icon: HeartIcon },
    { id: 'health', label: t('profile.goalHealth'), icon: SparklesIcon },
    { id: 'weight', label: t('profile.goalWeight'), icon: ScaleIcon },
  ] as const;

  const distances = [
    { id: '5k', label: '5K' },
    { id: '10k', label: '10K' },
    { id: 'half_marathon', label: t('profile.halfMarathon') },
    { id: 'marathon', label: t('profile.marathon') },
    { id: 'ultra', label: t('profile.ultra') },
  ] as const;

  const experienceLevels = [
    { id: 'beginner', label: t('profile.beginner'), desc: t('profile.beginnerDesc') },
    { id: 'intermediate', label: t('profile.intermediate'), desc: t('profile.intermediateDesc') },
    { id: 'advanced', label: t('profile.advanced'), desc: t('profile.advancedDesc') },
  ] as const;

  return (
    <div className="space-y-6 animate-slideUp">
      {/* Primary goal */}
      <div>
        <label className="block text-sm font-medium text-gray-200 mb-3">
          {t('profile.primaryGoalLabel')}
        </label>
        <div className="grid grid-cols-2 gap-3">
          {goals.map((goal) => (
            <SelectableCard
              key={goal.id}
              isSelected={profile.primaryGoal === goal.id}
              onClick={() => onUpdate({ primaryGoal: goal.id })}
            >
              <goal.icon className="w-5 h-5 text-teal-400 mb-2" />
              <span className="text-sm font-medium">{goal.label}</span>
            </SelectableCard>
          ))}
        </div>
      </div>

      {/* Race distance (conditional) */}
      {profile.primaryGoal === 'race' && (
        <div className="animate-slideUp">
          <label className="block text-sm font-medium text-gray-200 mb-3">
            {t('profile.raceDistanceLabel')}
          </label>
          <div className="flex flex-wrap gap-2">
            {distances.map((dist) => (
              <button
                key={dist.id}
                onClick={() => onUpdate({ raceDistance: dist.id })}
                className={clsx(
                  'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                  profile.raceDistance === dist.id
                    ? 'bg-teal-500 text-white'
                    : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                )}
              >
                {dist.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Weekly hours */}
      <div>
        <label className="block text-sm font-medium text-gray-200 mb-3">
          {t('profile.weeklyHoursLabel')}
        </label>
        <div className="flex items-center gap-4">
          <input
            type="range"
            min="1"
            max="20"
            value={profile.weeklyHours || 5}
            onChange={(e) => onUpdate({ weeklyHours: Number(e.target.value) })}
            className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-teal-500"
          />
          <span className="text-lg font-semibold text-teal-400 min-w-[4rem] text-right">
            {profile.weeklyHours || 5}h
          </span>
        </div>
        <p className="text-xs text-gray-500 mt-1">{t('profile.weeklyHoursHint')}</p>
      </div>

      {/* Experience level */}
      <div>
        <label className="block text-sm font-medium text-gray-200 mb-3">
          {t('profile.experienceLabel')}
        </label>
        <div className="space-y-2">
          {experienceLevels.map((level) => (
            <button
              key={level.id}
              onClick={() => onUpdate({ experienceLevel: level.id })}
              className={clsx(
                'w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors',
                profile.experienceLevel === level.id
                  ? 'bg-teal-500/20 border border-teal-500/50'
                  : 'bg-gray-800 border border-transparent hover:bg-gray-700'
              )}
            >
              <div
                className={clsx(
                  'w-4 h-4 rounded-full border-2 flex items-center justify-center',
                  profile.experienceLevel === level.id
                    ? 'border-teal-500 bg-teal-500'
                    : 'border-gray-600'
                )}
              >
                {profile.experienceLevel === level.id && (
                  <div className="w-2 h-2 rounded-full bg-white" />
                )}
              </div>
              <div>
                <div className="text-sm font-medium text-gray-100">{level.label}</div>
                <div className="text-xs text-gray-400">{level.desc}</div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// Zones Section
function ZonesSection({
  profile,
  onUpdate,
}: {
  profile: OnboardingProfile;
  onUpdate: (updates: Partial<OnboardingProfile>) => void;
}) {
  const t = useTranslations('onboarding');

  const zoneMethods = [
    { id: 'auto', label: t('profile.zoneAuto'), desc: t('profile.zoneAutoDesc') },
    { id: 'lthr', label: t('profile.zoneLthr'), desc: t('profile.zoneLthrDesc') },
    { id: 'max_hr', label: t('profile.zoneMaxHr'), desc: t('profile.zoneMaxHrDesc') },
    { id: 'manual', label: t('profile.zoneManual'), desc: t('profile.zoneManualDesc') },
  ] as const;

  return (
    <div className="space-y-6 animate-slideUp">
      <div>
        <label className="block text-sm font-medium text-gray-200 mb-3">
          {t('profile.zoneMethodLabel')}
        </label>
        <div className="space-y-2">
          {zoneMethods.map((method) => (
            <button
              key={method.id}
              onClick={() => onUpdate({ zoneMethod: method.id })}
              className={clsx(
                'w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors',
                profile.zoneMethod === method.id
                  ? 'bg-teal-500/20 border border-teal-500/50'
                  : 'bg-gray-800 border border-transparent hover:bg-gray-700'
              )}
            >
              <div
                className={clsx(
                  'w-4 h-4 rounded-full border-2 flex items-center justify-center',
                  profile.zoneMethod === method.id
                    ? 'border-teal-500 bg-teal-500'
                    : 'border-gray-600'
                )}
              >
                {profile.zoneMethod === method.id && (
                  <div className="w-2 h-2 rounded-full bg-white" />
                )}
              </div>
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-100">{method.label}</div>
                <div className="text-xs text-gray-400">{method.desc}</div>
              </div>
              {method.id === 'auto' && (
                <span className="text-xs font-medium text-teal-400 bg-teal-500/20 px-2 py-1 rounded">
                  {t('profile.recommended')}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* LTHR input */}
      {profile.zoneMethod === 'lthr' && (
        <div className="animate-slideUp">
          <label className="block text-sm font-medium text-gray-200 mb-2">
            {t('profile.lthrLabel')}
          </label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min="100"
              max="220"
              value={profile.lthr || ''}
              onChange={(e) => onUpdate({ lthr: Number(e.target.value) })}
              placeholder="165"
              className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 focus:outline-none"
            />
            <span className="text-gray-400">bpm</span>
          </div>
          <p className="text-xs text-gray-500 mt-1">{t('profile.lthrHint')}</p>
        </div>
      )}

      {/* Max HR input */}
      {profile.zoneMethod === 'max_hr' && (
        <div className="animate-slideUp">
          <label className="block text-sm font-medium text-gray-200 mb-2">
            {t('profile.maxHrLabel')}
          </label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min="140"
              max="240"
              value={profile.maxHr || ''}
              onChange={(e) => onUpdate({ maxHr: Number(e.target.value) })}
              placeholder="185"
              className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 focus:outline-none"
            />
            <span className="text-gray-400">bpm</span>
          </div>
          <p className="text-xs text-gray-500 mt-1">{t('profile.maxHrHint')}</p>
        </div>
      )}

      {/* Info card for auto method */}
      {profile.zoneMethod === 'auto' && (
        <Card variant="outlined" padding="sm" className="animate-slideUp">
          <div className="flex items-start gap-3">
            <div className="shrink-0 w-8 h-8 rounded-lg bg-teal-500/20 flex items-center justify-center">
              <SparklesIcon className="w-4 h-4 text-teal-400" />
            </div>
            <div>
              <p className="text-sm text-gray-300">{t('profile.zoneAutoInfo')}</p>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

// Preferences Section
function PreferencesSection({
  profile,
  onUpdate,
}: {
  profile: OnboardingProfile;
  onUpdate: (updates: Partial<OnboardingProfile>) => void;
}) {
  const t = useTranslations('onboarding');

  return (
    <div className="space-y-6 animate-slideUp">
      {/* Units */}
      <div>
        <label className="block text-sm font-medium text-gray-200 mb-3">
          {t('profile.unitsLabel')}
        </label>
        <div className="grid grid-cols-2 gap-3">
          <SelectableCard
            isSelected={profile.units === 'metric'}
            onClick={() => onUpdate({ units: 'metric' })}
          >
            <span className="text-2xl mb-2">km</span>
            <span className="text-sm font-medium">{t('profile.metric')}</span>
            <span className="text-xs text-gray-500">km, kg, m</span>
          </SelectableCard>
          <SelectableCard
            isSelected={profile.units === 'imperial'}
            onClick={() => onUpdate({ units: 'imperial' })}
          >
            <span className="text-2xl mb-2">mi</span>
            <span className="text-sm font-medium">{t('profile.imperial')}</span>
            <span className="text-xs text-gray-500">mi, lb, ft</span>
          </SelectableCard>
        </div>
      </div>

      {/* Ready to go message */}
      <Card variant="default" padding="md" className="text-center">
        <div className="text-4xl mb-3">🎉</div>
        <h3 className="text-lg font-semibold text-gray-100 mb-2">
          {t('profile.readyTitle')}
        </h3>
        <p className="text-sm text-gray-400">{t('profile.readyDesc')}</p>
      </Card>
    </div>
  );
}

// Helper Components
function SelectableCard({
  children,
  isSelected,
  onClick,
}: {
  children: React.ReactNode;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-all',
        'focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 focus:ring-offset-gray-950',
        isSelected
          ? 'border-teal-500 bg-teal-500/10 text-gray-100'
          : 'border-gray-700 bg-gray-900 text-gray-300 hover:border-gray-600 hover:bg-gray-800/50'
      )}
    >
      {children}
    </button>
  );
}

// Icon Components
function TrophyIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
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

function HeartIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"
      />
    </svg>
  );
}

function SparklesIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
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

function ScaleIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 3v17.25m0 0c-1.472 0-2.882.265-4.185.75M12 20.25c1.472 0 2.882.265 4.185.75M18.75 4.97A48.416 48.416 0 0012 4.5c-2.291 0-4.545.16-6.75.47m13.5 0c1.01.143 2.01.317 3 .52m-3-.52l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.988 5.988 0 01-2.031.352 5.988 5.988 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L18.75 4.971zm-16.5.52c.99-.203 1.99-.377 3-.52m0 0l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.989 5.989 0 01-2.031.352 5.989 5.989 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L5.25 4.971z"
      />
    </svg>
  );
}

export default ProfileStep;
