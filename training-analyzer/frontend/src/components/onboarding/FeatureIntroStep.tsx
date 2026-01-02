'use client';

import { useTranslations } from 'next-intl';
import { clsx } from 'clsx';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useOnboarding } from '@/contexts/onboarding-context';

interface FeatureIntroProps {
  onDismiss?: () => void;
  className?: string;
}

interface FeatureWeek {
  week: number;
  features: FeatureInfo[];
}

interface FeatureInfo {
  id: string;
  titleKey: string;
  descKey: string;
  icon: React.ComponentType<{ className?: string }>;
  route?: string;
  isLocked?: boolean;
  lockedLevel?: number;
}

// Feature configuration by week
const FEATURE_WEEKS: FeatureWeek[] = [
  {
    week: 1,
    features: [
      {
        id: 'dashboard',
        titleKey: 'featureIntro.dashboardTitle',
        descKey: 'featureIntro.dashboardDesc',
        icon: DashboardIcon,
        route: '/',
      },
      {
        id: 'workouts',
        titleKey: 'featureIntro.workoutsTitle',
        descKey: 'featureIntro.workoutsDesc',
        icon: WorkoutIcon,
        route: '/workouts',
      },
    ],
  },
  {
    week: 2,
    features: [
      {
        id: 'metrics-why',
        titleKey: 'featureIntro.metricsWhyTitle',
        descKey: 'featureIntro.metricsWhyDesc',
        icon: QuestionIcon,
      },
      {
        id: 'zones',
        titleKey: 'featureIntro.zonesTitle',
        descKey: 'featureIntro.zonesDesc',
        icon: ZonesIcon,
        route: '/zones',
      },
    ],
  },
  {
    week: 3,
    features: [
      {
        id: 'achievements',
        titleKey: 'featureIntro.achievementsTitle',
        descKey: 'featureIntro.achievementsDesc',
        icon: TrophyIcon,
        route: '/achievements',
      },
      {
        id: 'progress',
        titleKey: 'featureIntro.progressTitle',
        descKey: 'featureIntro.progressDesc',
        icon: ChartIcon,
        route: '/achievements',
      },
    ],
  },
  {
    week: 4,
    features: [
      {
        id: 'ai-chat-preview',
        titleKey: 'featureIntro.aiChatTitle',
        descKey: 'featureIntro.aiChatDesc',
        icon: AIIcon,
        route: '/chat',
        isLocked: true,
        lockedLevel: 8,
      },
      {
        id: 'plans-preview',
        titleKey: 'featureIntro.plansTitle',
        descKey: 'featureIntro.plansDesc',
        icon: PlansIcon,
        route: '/plans',
        isLocked: true,
        lockedLevel: 10,
      },
    ],
  },
];

export function FeatureIntroStep({ onDismiss, className }: FeatureIntroProps) {
  const t = useTranslations('onboarding');
  const { featureIntro, markFeatureSeen, hasSeenFeature } = useOnboarding();

  const currentWeekData = FEATURE_WEEKS.find((w) => w.week === featureIntro.currentWeek);

  if (!currentWeekData) return null;

  // Get unseen features for current week
  const unseenFeatures = currentWeekData.features.filter(
    (f) => !hasSeenFeature(f.id)
  );

  if (unseenFeatures.length === 0) return null;

  const handleFeatureSeen = (featureId: string) => {
    markFeatureSeen(featureId);
  };

  const handleDismissAll = () => {
    unseenFeatures.forEach((f) => markFeatureSeen(f.id));
    onDismiss?.();
  };

  return (
    <div className={clsx('space-y-4', className)}>
      {/* Week header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-teal-400">
            {t('featureIntro.weekLabel', { week: featureIntro.currentWeek })}
          </h3>
          <p className="text-sm text-gray-400">{t('featureIntro.newFeatures')}</p>
        </div>
        <button
          onClick={handleDismissAll}
          className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          {t('featureIntro.dismissAll')}
        </button>
      </div>

      {/* Feature cards */}
      <div className="space-y-3">
        {unseenFeatures.map((feature, index) => (
          <FeatureCard
            key={feature.id}
            feature={feature}
            onSeen={() => handleFeatureSeen(feature.id)}
            delay={index * 0.1}
          />
        ))}
      </div>
    </div>
  );
}

function FeatureCard({
  feature,
  onSeen,
  delay,
}: {
  feature: FeatureInfo;
  onSeen: () => void;
  delay: number;
}) {
  const t = useTranslations('onboarding');
  const Icon = feature.icon;

  return (
    <Card
      variant="interactive"
      padding="sm"
      className="animate-slideUp"
      style={{ animationDelay: `${delay}s` }}
    >
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div
          className={clsx(
            'shrink-0 w-10 h-10 rounded-lg flex items-center justify-center',
            feature.isLocked ? 'bg-gray-700' : 'bg-teal-500/20'
          )}
        >
          <Icon
            className={clsx(
              'w-5 h-5',
              feature.isLocked ? 'text-gray-500' : 'text-teal-400'
            )}
          />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-semibold text-gray-100">
              {t(feature.titleKey)}
            </h4>
            {feature.isLocked && feature.lockedLevel !== undefined && (
              <span className="inline-flex items-center gap-1 text-xs text-yellow-500 bg-yellow-500/10 px-2 py-0.5 rounded-full">
                <LockIcon className="w-3 h-3" />
                {t('featureIntro.unlocksAtLevel', { level: feature.lockedLevel })}
              </span>
            )}
            {!feature.isLocked && (
              <span className="text-xs text-teal-400 bg-teal-500/10 px-2 py-0.5 rounded-full">
                {t('featureIntro.new')}
              </span>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-1">{t(feature.descKey)}</p>
        </div>

        {/* Action */}
        <div className="shrink-0">
          {feature.isLocked ? (
            <button
              onClick={onSeen}
              className="p-2 text-gray-500 hover:text-gray-300 transition-colors"
              aria-label={t('featureIntro.dismiss')}
            >
              <CloseIcon className="w-4 h-4" />
            </button>
          ) : (
            <Button variant="ghost" size="sm" onClick={onSeen}>
              {t('featureIntro.gotIt')}
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}

// Compact version for inline hints
export function FeatureHint({
  featureId,
  children,
  className,
}: {
  featureId: string;
  children: React.ReactNode;
  className?: string;
}) {
  const t = useTranslations('onboarding');
  const { hasSeenFeature, markFeatureSeen } = useOnboarding();

  if (hasSeenFeature(featureId)) return null;

  return (
    <div
      className={clsx(
        'relative bg-teal-500/10 border border-teal-500/30 rounded-lg p-3 mb-4 animate-slideUp',
        className
      )}
    >
      <button
        onClick={() => markFeatureSeen(featureId)}
        className="absolute top-2 right-2 text-gray-500 hover:text-gray-300 transition-colors"
        aria-label={t('featureIntro.dismiss')}
      >
        <CloseIcon className="w-4 h-4" />
      </button>
      <div className="flex items-start gap-2 pr-6">
        <InfoIcon className="w-4 h-4 text-teal-400 shrink-0 mt-0.5" />
        <p className="text-sm text-gray-300">{children}</p>
      </div>
    </div>
  );
}

// Icon Components
function DashboardIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z"
      />
    </svg>
  );
}

function WorkoutIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
      />
    </svg>
  );
}

function QuestionIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z"
      />
    </svg>
  );
}

function ZonesIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"
      />
    </svg>
  );
}

function TrophyIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M16.5 18.75h-9m9 0a3 3 0 013 3h-15a3 3 0 013-3m9 0v-3.375c0-.621-.503-1.125-1.125-1.125h-.871M7.5 18.75v-3.375c0-.621.504-1.125 1.125-1.125h.872m5.007 0H9.497m5.007 0a7.454 7.454 0 01-.982-3.172M9.497 14.25a7.454 7.454 0 00.981-3.172M5.25 4.236c-.982.143-1.954.317-2.916.52A6.003 6.003 0 007.73 9.728M5.25 4.236V4.5c0 2.108.966 3.99 2.48 5.228M5.25 4.236V2.721C7.456 2.41 9.71 2.25 12 2.25c2.291 0 4.545.16 6.75.47v1.516M7.73 9.728a6.726 6.726 0 002.748 1.35m8.272-6.842V4.5c0 2.108-.966 3.99-2.48 5.228m2.48-5.492a46.32 46.32 0 012.916.52 6.003 6.003 0 01-5.395 4.972m0 0a6.726 6.726 0 01-2.749 1.35m0 0a6.772 6.772 0 01-3.044 0"
      />
    </svg>
  );
}

function ChartIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
      />
    </svg>
  );
}

function AIIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z"
      />
    </svg>
  );
}

function PlansIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5m-9-6h.008v.008H12v-.008zM12 15h.008v.008H12V15zm0 2.25h.008v.008H12v-.008zM9.75 15h.008v.008H9.75V15zm0 2.25h.008v.008H9.75v-.008zM7.5 15h.008v.008H7.5V15zm0 2.25h.008v.008H7.5v-.008zm6.75-4.5h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008V15zm0 2.25h.008v.008h-.008v-.008zm2.25-4.5h.008v.008H16.5v-.008zm0 2.25h.008v.008H16.5V15z"
      />
    </svg>
  );
}

function LockIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
      />
    </svg>
  );
}

function CloseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

function InfoIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"
      />
    </svg>
  );
}

export default FeatureIntroStep;
