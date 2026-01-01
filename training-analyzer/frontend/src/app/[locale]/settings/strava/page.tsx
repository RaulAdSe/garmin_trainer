'use client';

import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { StravaConnection } from '@/components/settings/StravaConnection';

export default function StravaSettingsPage() {
  const t = useTranslations('strava');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="animate-fadeIn">
        <div className="flex items-center gap-2 text-sm text-gray-400 mb-4">
          <Link href="/" className="hover:text-gray-300 transition-colors">
            {t('breadcrumbHome')}
          </Link>
          <span>/</span>
          <span className="text-gray-300">{t('breadcrumbSettings')}</span>
        </div>

        <h1 className="text-xl sm:text-2xl font-bold text-gray-100">
          {t('pageTitle')}
        </h1>
        <p className="text-sm sm:text-base text-gray-400 mt-1">
          {t('pageSubtitle')}
        </p>
      </div>

      {/* Strava Connection Card */}
      <div className="max-w-2xl animate-slideUp">
        <StravaConnection />
      </div>

      {/* Help Section */}
      <div
        className="max-w-2xl bg-gray-900 rounded-lg border border-gray-800 p-6 animate-slideUp"
        style={{ animationDelay: '0.1s' }}
      >
        <h2 className="text-lg font-semibold text-gray-100 mb-4">
          {t('howItWorksTitle')}
        </h2>
        <ul className="space-y-3 text-sm text-gray-400">
          <li className="flex items-start gap-3">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-[#FC4C02]/20 text-[#FC4C02] text-xs font-medium shrink-0">
              1
            </span>
            <span>{t('howItWorksStep1')}</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-[#FC4C02]/20 text-[#FC4C02] text-xs font-medium shrink-0">
              2
            </span>
            <span>{t('howItWorksStep2')}</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-[#FC4C02]/20 text-[#FC4C02] text-xs font-medium shrink-0">
              3
            </span>
            <span>{t('howItWorksStep3')}</span>
          </li>
        </ul>
      </div>

      {/* Features Section */}
      <div
        className="max-w-2xl bg-gray-900 rounded-lg border border-gray-800 p-6 animate-slideUp"
        style={{ animationDelay: '0.2s' }}
      >
        <h2 className="text-lg font-semibold text-gray-100 mb-4">
          {t('featuresTitle')}
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <FeatureCard
            icon={<AutoSyncIcon />}
            title={t('featureAutoSync')}
            description={t('featureAutoSyncDesc')}
          />
          <FeatureCard
            icon={<AnalysisIcon />}
            title={t('featureAnalysis')}
            description={t('featureAnalysisDesc')}
          />
          <FeatureCard
            icon={<ShareIcon />}
            title={t('featureShare')}
            description={t('featureShareDesc')}
          />
          <FeatureCard
            icon={<CustomizeIcon />}
            title={t('featureCustomize')}
            description={t('featureCustomizeDesc')}
          />
        </div>
      </div>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="p-4 bg-gray-800/50 rounded-lg">
      <div className="flex items-center gap-3 mb-2">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-[#FC4C02]/20 text-[#FC4C02]">
          {icon}
        </div>
        <h3 className="text-sm font-medium text-gray-200">{title}</h3>
      </div>
      <p className="text-xs text-gray-500">{description}</p>
    </div>
  );
}

// Feature icons
function AutoSyncIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
      />
    </svg>
  );
}

function AnalysisIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
      />
    </svg>
  );
}

function ShareIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"
      />
    </svg>
  );
}

function CustomizeIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
      />
    </svg>
  );
}
