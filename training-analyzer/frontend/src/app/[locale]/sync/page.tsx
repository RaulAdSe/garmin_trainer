'use client';

import { useTranslations } from 'next-intl';
import { useRouter } from '@/i18n/navigation';
import { GarminSync } from '@/components/garmin/GarminSync';
import { GarminSyncResponse } from '@/lib/api-client';

export default function SyncPage() {
  const t = useTranslations('sync');
  const router = useRouter();

  const handleSyncComplete = (result: GarminSyncResponse) => {
    // Optionally redirect to workouts after successful sync
    console.log('Sync completed:', result);
  };

  const handleClose = () => {
    router.back();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="animate-fadeIn">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-100">
          {t('title')}
        </h1>
        <p className="text-sm sm:text-base text-gray-400 mt-1">
          {t('subtitle')}
        </p>
      </div>

      {/* Sync Component */}
      <div className="max-w-lg animate-slideUp">
        <GarminSync
          onSyncComplete={handleSyncComplete}
          onClose={handleClose}
        />
      </div>

      {/* Help Section */}
      <div className="max-w-lg bg-gray-900 rounded-lg border border-gray-800 p-6 animate-slideUp" style={{ animationDelay: '0.1s' }}>
        <h2 className="text-lg font-semibold text-gray-100 mb-4">
          {t('howItWorks')}
        </h2>
        <ul className="space-y-3 text-sm text-gray-400">
          <li className="flex items-start gap-3">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-teal-900/50 text-teal-400 text-xs font-medium shrink-0">
              1
            </span>
            <span>
              {t('howItWorksDesc')}
            </span>
          </li>
          <li className="flex items-start gap-3">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-teal-900/50 text-teal-400 text-xs font-medium shrink-0">
              2
            </span>
            <span>
              {t('selectDays')}
            </span>
          </li>
          <li className="flex items-start gap-3">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-teal-900/50 text-teal-400 text-xs font-medium shrink-0">
              3
            </span>
            <span>
              {t('activitiesStored')}
            </span>
          </li>
        </ul>
      </div>

      {/* Supported Features */}
      <div className="max-w-lg bg-gray-900 rounded-lg border border-gray-800 p-6 animate-slideUp" style={{ animationDelay: '0.2s' }}>
        <h2 className="text-lg font-semibold text-gray-100 mb-4">
          {t('supportedTypes')}
        </h2>
        <div className="flex flex-wrap gap-2">
          {(['activityRunning', 'activityCycling', 'activitySwimming', 'activityWalking', 'activityHiking', 'activityStrength'] as const).map((typeKey) => (
            <span
              key={typeKey}
              className="px-3 py-1.5 bg-gray-800 text-gray-300 text-sm rounded-full"
            >
              {t(typeKey)}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
