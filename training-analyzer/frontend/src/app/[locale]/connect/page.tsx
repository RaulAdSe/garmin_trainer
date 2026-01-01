'use client';

import { useTranslations } from 'next-intl';
import { GarminSync } from '@/components/garmin/GarminSync';
import { StravaConnection } from '@/components/settings/StravaConnection';
import { GarminSyncResponse } from '@/lib/api-client';

export default function ConnectPage() {
  const t = useTranslations('connect');

  const handleSyncComplete = (result: GarminSyncResponse) => {
    console.log('Sync completed:', result);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="animate-fadeIn">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-100">
          {t('title')}
        </h1>
        <p className="text-sm sm:text-base text-gray-400 mt-1">
          {t('subtitle')}
        </p>
      </div>

      {/* Connection Cards Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Garmin Section */}
        <div className="space-y-4 animate-slideUp">
          <h2 className="text-lg font-semibold text-gray-200 flex items-center gap-2">
            <GarminIcon className="w-5 h-5 text-blue-400" />
            Garmin Connect
          </h2>
          <GarminSync onSyncComplete={handleSyncComplete} />
        </div>

        {/* Strava Section */}
        <div className="space-y-4 animate-slideUp" style={{ animationDelay: '0.1s' }}>
          <h2 className="text-lg font-semibold text-gray-200 flex items-center gap-2">
            <StravaIcon className="w-5 h-5" />
            Strava
          </h2>
          <StravaConnection />
        </div>
      </div>
    </div>
  );
}

function GarminIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
    </svg>
  );
}

function StravaIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="#FC4C02">
      <path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066m-7.008-5.599l2.836 5.598h4.172L10.463 0l-7 13.828h4.169" />
    </svg>
  );
}
